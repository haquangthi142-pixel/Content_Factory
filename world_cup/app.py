import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests
from datetime import datetime

from world_cup import api
from world_cup import db
from world_cup.components import (
    GLOBAL_CSS,
    match_card,
    group_standings_table,
    teams_grid,
)

try:
    api.API_KEY = st.secrets["API_FOOTBALL_KEY"]
except KeyError:
    pass

db.init_db()

if "betting_user" not in st.session_state:
    st.session_state.betting_user = None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_matches():
    return api.fetch_matches()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_standings():
    return api.fetch_standings()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_teams():
    return api.fetch_teams()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_group_standings():
    return api.fetch_group_standings()


def _render_betting_game():
    user = st.session_state.betting_user

    if user is None:
        st.title("🏆 World Cup 2026 Betting Game")
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.subheader("Sign In / Register")
            phone = st.text_input("Phone Number", placeholder="+84xxxxxxxxx", key="login_phone")
            name = st.text_input("Full Name", placeholder="Nguyen Van A", key="login_name")
            if st.button("Enter Game", use_container_width=True, key="login_btn"):
                if phone.strip() and name.strip():
                    u = db.get_user_by_phone(phone.strip())
                    if not u:
                        uid = db.register_user(phone.strip(), name.strip())
                        st.session_state.betting_user = dict(db.get_user(uid))
                        st.rerun()
                    elif u["full_name"].strip().lower() != name.strip().lower():
                        st.error(f"This phone number is already registered to **{u['full_name']}**.")
                    else:
                        st.session_state.betting_user = dict(u)
                        st.rerun()
                else:
                    st.warning("Please fill in both fields.")
        return

    # --- Logged in ---
    user_data = db.get_user(user["id"])
    coins = user_data["current_coins"]
    lb = db.get_leaderboard()
    rank = next((i + 1 for i, r in enumerate(lb) if r["id"] == user["id"]), "?")

    # Header
    cols = st.columns([3, 1, 1, 1])
    with cols[0]:
        st.title("🏆 Betting Game")
    with cols[1]:
        st.metric("Wallet", f"{coins:,} Coins")
    with cols[2]:
        st.metric("Rank", f"#{rank}")
    with cols[3]:
        st.caption(f"👤 {user_data['full_name']}")
        if st.button("Logout", key="bet_logout"):
            st.session_state.betting_user = None
            st.rerun()
    st.markdown("---")

    tab_bet, tab_mybets, tab_leaderboard, tab_missions = st.tabs([
        "⚽ Place Bets", "📋 My Bets", "🏅 Leaderboard", "🎯 Missions"
    ])

    # -- Place Bets --
    with tab_bet:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader("Upcoming & Live Matches")
        with c2:
            if st.button("🔄 Sync Matches", use_container_width=True):
                with st.spinner("Syncing..."):
                    n = db.sync_matches_from_api()
                st.success(f"Synced {n} matches")
                st.rerun()

        st.info("💰 Payout: 2x your bet on correct outcome. Bets must be in multiples of 10 coins.")

        conn = db.get_connection()
        matches = conn.execute(
            "SELECT * FROM matches WHERE status != 'Finished' ORDER BY match_time LIMIT 50"
        ).fetchall()
        conn.close()

        if not matches:
            st.info("No upcoming matches. Click 'Sync Matches' to load the schedule.")
        else:
            for m in matches:
                match_id = m["match_id"]
                match_time_str = m["match_time"][:16].replace("T", " ")
                conn = db.get_connection()
                existing = conn.execute(
                    "SELECT * FROM bets WHERE user_id = ? AND match_id = ?",
                    (user["id"], match_id),
                ).fetchone()
                conn.close()

                col1, col2 = st.columns([4, 1])
                with col1:
                    badge = "🔴 LIVE" if m["status"] == "Live" else "📅 Upcoming"
                    st.markdown(
                        f"**{m['team_a']}** vs **{m['team_b']}**  "
                        f"<span style='font-size:0.8rem;color:var(--text-muted)'>{badge} · {match_time_str} UTC</span>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    if existing:
                        bm = {"A": f"{m['team_a']} Win", "B": f"{m['team_b']} Win", "DRAW": "Draw"}
                        st.caption(f"✅ Bet: {bm.get(existing['bet_choice'], existing['bet_choice'])} — {existing['bet_amount']} coins")
                    else:
                        ek = f"bet_expand_{match_id}"
                        if ek not in st.session_state:
                            st.session_state[ek] = False
                        if st.button("Place Bet", key=f"betbtn_{match_id}"):
                            st.session_state[ek] = not st.session_state[ek]
                            st.rerun()

                if existing is None and st.session_state.get(f"bet_expand_{match_id}", False):
                    st.markdown("---")
                    choice = st.radio(
                        "Pick outcome:",
                        [f"{m['team_a']} Win", "Draw", f"{m['team_b']} Win"],
                        key=f"choice_{match_id}", horizontal=True,
                    )
                    cm = {
                        f"{m['team_a']} Win": "A",
                        "Draw": "DRAW",
                        f"{m['team_b']} Win": "B",
                    }
                    amt_key = f"amount_{match_id}"
                    if amt_key not in st.session_state:
                        st.session_state[amt_key] = 50

                    ca, cb, cc = st.columns([1, 1, 1])
                    with ca:
                        st.session_state[amt_key] = st.number_input(
                            "Bet amount", min_value=10, max_value=coins,
                            value=st.session_state[amt_key], step=10, key=f"num_{match_id}",
                        )
                    with cb:
                        for sv in [10, 50, 100]:
                            if st.button(f"+{sv}", key=f"qs_{match_id}_{sv}"):
                                st.session_state[amt_key] = min(st.session_state[amt_key] + sv, coins)
                                st.rerun()
                    with cc:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Confirm Bet ✅", key=f"confirm_{match_id}", use_container_width=True):
                            try:
                                db.place_bet(user["id"], match_id, cm[choice], st.session_state[amt_key])
                                st.success(f"Bet placed! {st.session_state[amt_key]} coins on {choice}")
                                st.session_state[f"bet_expand_{match_id}"] = False
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                st.markdown("---")

    # -- My Bets --
    with tab_mybets:
        st.subheader("My Betting History")
        conn = db.get_connection()
        my_bets = conn.execute(
            """SELECT b.*, m.team_a, m.team_b, m.match_time, m.status as match_status, m.result
               FROM bets b JOIN matches m ON b.match_id = m.match_id
               WHERE b.user_id = ? ORDER BY b.created_at DESC LIMIT 50""",
            (user["id"],),
        ).fetchall()
        conn.close()

        if not my_bets:
            st.info("No bets placed yet.")
        else:
            sc = {"Pending": "var(--accent-live)", "Won": "var(--accent-done)",
                  "Lost": "var(--accent-danger)", "Refunded": "#95a5a6"}
            for b in my_bets:
                cd = {"A": f"{b['team_a']} Win", "B": f"{b['team_b']} Win", "DRAW": "Draw"}
                st.markdown(
                    f"<div style='background:var(--bg-card);border:1px solid var(--border-subtle);"
                    f"border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;"
                    f"display:flex;justify-content:space-between;align-items:center'>"
                    f"<div><strong>{b['team_a']} vs {b['team_b']}</strong><br>"
                    f"<span style='font-size:0.8rem;color:var(--text-muted)'>"
                    f"Choice: {cd.get(b['bet_choice'], b['bet_choice'])} · {b['bet_amount']} coins</span></div>"
                    f"<div style='text-align:right'>"
                    f"<span style='background:{sc.get(b['status'], 'gray')};color:white;"
                    f"padding:2px 10px;border-radius:10px;font-size:0.75rem'>{b['status']}</span>"
                    f"<br><span style='font-size:0.7rem;color:var(--text-muted)'>{b['created_at'][:16]}</span></div></div>",
                    unsafe_allow_html=True,
                )

    # -- Leaderboard --
    with tab_leaderboard:
        st.subheader("🏅 Company Leaderboard")
        lb = db.get_leaderboard()
        if not lb:
            st.info("No participants yet.")
        else:
            medals = {0: "🥇", 1: "🥈", 2: "🥉"}
            for i, row in enumerate(lb):
                medal = medals.get(i, "")
                if i == 0:
                    bg = "background: linear-gradient(135deg, #3d2e00 0%, #5a4200 100%); border: 1px solid rgba(212,168,67,0.5);"
                elif i == 1:
                    bg = "background: linear-gradient(135deg, #2a2a2a 0%, #3a3a3a 100%); border: 1px solid rgba(192,192,192,0.4);"
                elif i == 2:
                    bg = "background: linear-gradient(135deg, #2d1a0a 0%, #3d2a0a 100%); border: 1px solid rgba(205,127,50,0.4);"
                else:
                    bg = "background: var(--bg-card); border: 1px solid var(--border-subtle);"
                hl = "font-weight:700; color: var(--gold-bright);" if i < 3 else ""
                st.markdown(
                    f"<div style='{bg} border-radius:8px; padding:0.6rem 1rem; margin-bottom:0.35rem; "
                    f"display:flex; justify-content:space-between; align-items:center'>"
                    f"<span style='font-size:1.2rem'>{medal} <strong>#{i+1}</strong> "
                    f"<span style='{hl}'>{row['full_name']}</span></span>"
                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.3rem;{hl}'>"
                    f"{row['current_coins']:,} coins</span></div>",
                    unsafe_allow_html=True,
                )

    # -- Missions --
    with tab_missions:
        st.subheader("🎯 Daily Missions — Earn Extra Coins")
        missions = [
            {"type": "share_facebook", "label": "📢 Share match schedule on Facebook", "reward": 50},
            {"type": "daily_login", "label": "🔔 Daily check-in", "reward": 20},
            {"type": "invite_friend", "label": "👥 Invite a colleague to join", "reward": 100},
        ]
        for mission in missions:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{mission['label']}**")
                st.caption(f"Reward: +{mission['reward']} coins")
            with c2:
                conn = db.get_connection()
                today = datetime.now().strftime("%Y-%m-%d")
                done = conn.execute(
                    """SELECT COUNT(*) as cnt FROM mission_logs
                       WHERE user_id = ? AND mission_type = ? AND DATE(completed_at) = ?""",
                    (user["id"], mission["type"], today),
                ).fetchone()["cnt"]
                conn.close()
                if done > 0:
                    st.success("Done ✓")
                else:
                    if st.button("Claim", key=f"mission_{mission['type']}"):
                        if mission["type"] == "share_facebook":
                            share_url = "https://www.facebook.com/sharer/sharer.php?u=https://www.fifa.com/worldcup"
                            st.markdown(
                                f"<a href='{share_url}' target='_blank'>Click here to share</a>, "
                                "then come back and click Claim again.",
                                unsafe_allow_html=True,
                            )
                        else:
                            db.complete_mission(user["id"], mission["type"], mission["reward"])
                            st.success(f"+{mission['reward']} coins!")
                            st.rerun()
            st.markdown("---")


st.set_page_config(
    page_title="World Cup 2026 Dashboard",
    page_icon="🏆",
    layout="wide",
)

st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)

st.title("🏆 World Cup 2026")
st.markdown(
    "<p style='color:var(--text-muted);font-family:Chakra Petch,sans-serif;margin-top:-0.5rem'>"
    "Host: USA · Canada · Mexico &nbsp;|&nbsp; "
    f"Data via football-data.org &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    "</p>",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    "<h2 style='font-family:Bebas Neue,sans-serif;letter-spacing:0.06em;margin-bottom:0'>"
    "🌍 WORLD CUP 2026</h2>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    "<p style='font-family:Chakra Petch,sans-serif;font-size:0.8rem;color:var(--text-muted)'>"
    "Host: USA, Canada, Mexico</p>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")
view = st.sidebar.radio(
    "Navigation",
    ["📊 Overview", "📅 Matches", "📋 Group Standings", "🌍 Teams", "🎮 Betting Game"],
    label_visibility="collapsed",
)

try:
    if view == "📊 Overview":
        col1, col2, col3 = st.columns(3)

        with st.spinner("Loading data..."):
            teams_data = fetch_teams()
            matches_data = fetch_matches()

        total_teams = teams_data.get("count", 0)
        all_matches = matches_data.get("matches", [])
        total_matches = matches_data.get("resultSet", {}).get("count", len(all_matches))
        finished = sum(1 for m in all_matches if m.get("status") == "FINISHED")
        scheduled = sum(1 for m in all_matches if m.get("status") in ("SCHEDULED", "TIMED"))

        with col1:
            st.metric("Teams", total_teams)
        with col2:
            st.metric("Total Matches", total_matches)
        with col3:
            st.metric("Completed", finished, f"{scheduled} remaining")

        st.markdown("---")
        st.subheader("Recent Results")
        finished_matches = [m for m in all_matches if m.get("status") == "FINISHED"]
        if finished_matches:
            for m in finished_matches[-6:]:
                match_card(m)
        else:
            st.info("No results yet — tournament hasn't started.")

        st.markdown("---")
        st.subheader("Upcoming Matches")
        upcoming = [m for m in all_matches if m.get("status") in ("SCHEDULED", "TIMED")]
        if upcoming:
            PAGE_SIZE = 5
            total = len(upcoming)
            total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            key_u = "overview_upcoming_page"
            if key_u not in st.session_state:
                st.session_state[key_u] = 1

            page = st.session_state[key_u]
            start = (page - 1) * PAGE_SIZE
            end = start + PAGE_SIZE
            st.caption(f"Showing {start + 1}–{min(end, total)} of {total} matches")
            for m in upcoming[start:end]:
                match_card(m)

            if total_pages > 1:
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.button("◀ Prev", key="overview_upcoming_prev", disabled=(page == 1),
                              on_click=lambda: st.session_state.update({key_u: page - 1}),
                              use_container_width=True)
                with c2:
                    st.markdown(
                        f"<div style='text-align:center;padding-top:6px;color:var(--text-muted)'>"
                        f"Page {page} of {total_pages}</div>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.button("Next ▶", key="overview_upcoming_next", disabled=(page == total_pages),
                              on_click=lambda: st.session_state.update({key_u: page + 1}),
                              use_container_width=True)
        else:
            st.info("No upcoming matches scheduled yet.")

        st.markdown("---")
        st.subheader("Group Standings Preview")
        groups = fetch_group_standings()
        if groups:
            group_standings_table(groups)
        else:
            st.info("Standings will appear once the tournament begins.")

    elif view == "📅 Matches":
        PAGE_SIZE = 10

        with st.spinner("Loading matches..."):
            matches_data = fetch_matches()
            all_matches = matches_data.get("matches", [])

        tab1, tab2, tab3 = st.tabs(["🔴 Live Now", "✅ Completed", "📅 Upcoming"])

        with tab1:
            live = [m for m in all_matches if m.get("status") in ("LIVE", "IN_PLAY", "PAUSED")]
            if live:
                for m in live:
                    match_card(m, expanded=True)
            else:
                st.info("No live World Cup matches right now.")

        with tab2:
            finished = [m for m in all_matches if m.get("status") == "FINISHED"]
            if finished:
                ordered = list(reversed(finished))
                total = len(ordered)
                total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
                key_r = "results_page"
                if key_r not in st.session_state:
                    st.session_state[key_r] = 1

                page = st.session_state[key_r]
                start = (page - 1) * PAGE_SIZE
                end = start + PAGE_SIZE
                st.caption(f"Showing {start + 1}–{min(end, total)} of {total} matches")
                for m in ordered[start:end]:
                    match_card(m, expanded=True)

                if total_pages > 1:
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        st.button("◀ Prev", key="results_prev", disabled=(page == 1),
                                  on_click=lambda: st.session_state.update({key_r: page - 1}),
                                  use_container_width=True)
                    with c2:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:6px;color:var(--text-muted)'>"
                            f"Page {page} of {total_pages}</div>",
                            unsafe_allow_html=True,
                        )
                    with c3:
                        st.button("Next ▶", key="results_next", disabled=(page == total_pages),
                                  on_click=lambda: st.session_state.update({key_r: page + 1}),
                                  use_container_width=True)
            else:
                st.info("No completed matches yet.")

        with tab3:
            PAGE_SIZE_UPCOMING = 5
            upcoming = [m for m in all_matches if m.get("status") in ("SCHEDULED", "TIMED")]
            if upcoming:
                total = len(upcoming)
                total_pages = max(1, (total + PAGE_SIZE_UPCOMING - 1) // PAGE_SIZE_UPCOMING)
                key_u = "upcoming_page"
                if key_u not in st.session_state:
                    st.session_state[key_u] = 1

                page = st.session_state[key_u]
                start = (page - 1) * PAGE_SIZE_UPCOMING
                end = start + PAGE_SIZE_UPCOMING
                st.caption(f"Showing {start + 1}–{min(end, total)} of {total} matches")
                for m in upcoming[start:end]:
                    match_card(m, expanded=True)

                if total_pages > 1:
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        st.button("◀ Prev", key="upcoming_prev", disabled=(page == 1),
                                  on_click=lambda: st.session_state.update({key_u: page - 1}),
                                  use_container_width=True)
                    with c2:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:6px;color:var(--text-muted)'>"
                            f"Page {page} of {total_pages}</div>",
                            unsafe_allow_html=True,
                        )
                    with c3:
                        st.button("Next ▶", key="upcoming_next", disabled=(page == total_pages),
                                  on_click=lambda: st.session_state.update({key_u: page + 1}),
                                  use_container_width=True)
            else:
                st.info("No upcoming matches scheduled yet.")

    elif view == "📋 Group Standings":
        st.subheader("World Cup 2026 — Group Stage Standings")
        with st.spinner("Loading standings..."):
            groups = fetch_group_standings()
            group_standings_table(groups)

    elif view == "🌍 Teams":
        st.subheader("World Cup 2026 — Participating Teams")
        with st.spinner("Loading teams..."):
            teams_data = fetch_teams()
            teams_grid(teams_data)

    elif view == "🎮 Betting Game":
        _render_betting_game()

except requests.exceptions.RequestException as e:
    st.error(f"API connection error: {e}")
except Exception as e:
    st.error(f"Error: {e}")
