import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests
import time
from datetime import datetime

from world_cup import api
from world_cup import db
from world_cup import betting_ui
from world_cup import admin as admin_panel
from world_cup.components import (
    GLOBAL_CSS,
    match_card,
    group_standings_table,
    teams_grid,
)

# api.py now handles st.secrets with .env fallback at module level.
# This keep as defense-in-depth in case api.py is reloaded or st.secrets changes.

db.init_db()

if "betting_user" not in st.session_state:
    st.session_state.betting_user = None
if "user" not in st.session_state:
    st.session_state.user = None


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


def _render_overview_quick_bet(api_match):
    """Show a compact 'Bet' button + inline bet slip in the Overview tab.

    Only appears when the user is logged in and the match exists in the DB.
    """
    user = st.session_state.get("user")
    if user is None:
        return

    db_match = db.get_match(api_match["id"])
    if db_match is None or db_match["status"] == "Finished":
        return

    user_data = db.get_user(user["id"])
    if user_data is None:
        return
    coins = user_data["current_coins"]
    match_id = db_match["match_id"]

    ek = f"overview_bet_{match_id}"
    if ek not in st.session_state:
        st.session_state[ek] = False

    # Toggle button — compact, right-aligned
    _, btn_col = st.columns([5, 1])
    with btn_col:
        label = "✕ Close" if st.session_state[ek] else "💰 Bet"
        if st.button(label, key=f"ov_btn_{match_id}", use_container_width=True):
            st.session_state[ek] = not st.session_state[ek]
            st.rerun()

    if not st.session_state[ek]:
        return

    # Expanded bet slip
    with st.container():
        st.markdown("---")
        st.caption(f"Quick Bet — **{db_match['team_a']}** vs **{db_match['team_b']}**")

        if coins < 10:
            st.error("Insufficient coins. Minimum bet is 10 coins.")
            return

        choice = st.radio(
            "Pick outcome:",
            [f"{db_match['team_a']} Win", "Draw", f"{db_match['team_b']} Win"],
            key=f"ov_choice_{match_id}",
            horizontal=True,
        )
        choice_map = {
            f"{db_match['team_a']} Win": "A",
            "Draw": "DRAW",
            f"{db_match['team_b']} Win": "B",
        }

        num_key = f"ov_num_{match_id}"
        if num_key not in st.session_state:
            st.session_state[num_key] = min(50, coins)

        # Quick-add + amount
        qc1, qc2, qc3, qc4 = st.columns([1, 1, 1, 2])
        with qc1:
            if st.button("+10", key=f"ov_qs_{match_id}_10"):
                st.session_state[num_key] = min(st.session_state[num_key] + 10, coins)
                st.rerun()
        with qc2:
            if st.button("+50", key=f"ov_qs_{match_id}_50"):
                st.session_state[num_key] = min(st.session_state[num_key] + 50, coins)
                st.rerun()
        with qc3:
            if st.button("+100", key=f"ov_qs_{match_id}_100"):
                st.session_state[num_key] = min(st.session_state[num_key] + 100, coins)
                st.rerun()
        with qc4:
            amount = st.number_input(
                "Amount", min_value=10, max_value=coins,
                step=10, key=num_key, label_visibility="collapsed",
            )

        if st.button("Confirm Bet  ✓", key=f"ov_confirm_{match_id}", use_container_width=True):
            try:
                db.place_bet(user["id"], match_id, choice_map[choice], amount)
                st.success(f"Bet placed! {amount} coins on {choice}")
                st.session_state[ek] = False
                st.rerun()
            except ValueError as e:
                st.error(str(e))


@st.dialog("Confirm Purchase Request", width="small")
def _purchase_confirm_dialog(user_id: int, vnd: int, est_coins: int):
    """Modal popup — player confirms a coin purchase request before sending."""
    st.markdown(f"### 🪙 {est_coins} coins")
    st.caption(f"Amount: **{vnd:,} VND** &nbsp;|&nbsp; Rate: 1,000 VND = 1 coin")
    st.markdown("---")
    st.caption("An admin will review and approve your request.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✓  Confirm", use_container_width=True, key="dialog_confirm"):
            try:
                req_id = db.request_purchase(user_id, vnd)
                st.session_state._purchase_success = f"Request #{req_id} sent! Awaiting admin approval."
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    with col2:
        if st.button("✕  Cancel", use_container_width=True, key="dialog_cancel"):
            st.rerun()


def _render_betting_game():
    # Bridge session state: app.py uses 'betting_user', betting_ui uses 'user'.
    # Only seed user from betting_user when user isn't already set (e.g. by a
    # just-completed login that triggered st.rerun before we could sync back).
    if st.session_state.user is None and st.session_state.betting_user is not None:
        st.session_state.user = st.session_state.betting_user

    if st.session_state.user is None:
        with st.container():
            betting_ui.render_login_screen()
        st.session_state.betting_user = st.session_state.user
        return

    # Auto-sync matches on first login (once per session)
    if not st.session_state.get("_matches_synced"):
        db.sync_matches_from_api()
        st.session_state._matches_synced = True

    user = st.session_state.user

    # Session timeout: 60 min idle -> logout
    now = time.time()
    if st.session_state.get("_last_activity") and (now - st.session_state["_last_activity"] > 3600):
        st.session_state.betting_user = None
        st.session_state.user = None
        st.session_state._last_activity = None
        st.warning("Session expired due to inactivity. Please log in again.")
        st.rerun()
    st.session_state["_last_activity"] = now

    user_data = db.get_user(user["id"])
    if user_data is None:
        st.session_state.betting_user = None
        st.session_state.user = None
        st.warning("Your account has been removed. Please re-register.")
        st.rerun()
    # Keep session state in sync with DB (admin may have credited coins, etc.)
    st.session_state.user = dict(user_data)
    coins = user_data["current_coins"]
    lb = db.get_leaderboard()
    rank = next((i + 1 for i, r in enumerate(lb) if r["id"] == user["id"]), "?")

    col_header, col_logout = st.columns([9, 1])
    with col_header:
        betting_ui.render_game_header(user_data, coins, rank)
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("←  Exit", key="bet_logout", use_container_width=True):
            st.session_state.betting_user = None
            st.session_state.user = None
            st.rerun()

    st.markdown("---")

    is_admin = st.session_state.get("admin_authenticated", False)

    if is_admin:
        tab_bet, tab_mybets, tab_leaderboard, tab_missions = st.tabs([
            "⚽  Place Bets", "📋  My Bets", "🏅  Leaderboard", "🎯  Missions"
        ])
    else:
        tab_bet, tab_mybets = st.tabs([
            "⚽  Place Bets", "📋  My Bets"
        ])

    with tab_bet:
        betting_ui.render_place_bets_tab(user["id"], coins)

    with tab_mybets:
        betting_ui.render_my_bets_tab(user["id"])

    if is_admin:
        with tab_leaderboard:
            betting_ui.render_leaderboard_tab()

        with tab_missions:
            betting_ui.render_missions_tab(user["id"])


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
    f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
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
    ["📊 Overview", "📅 Matches", "📋 Group Standings", "🌍 Teams", "🎮 Betting Game", "🔒 Admin"],
    label_visibility="collapsed",
)

# Always-visible Buy Coins in sidebar (when logged in)
if st.session_state.get("user") is not None:
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<span style='font-family:Bebas Neue,sans-serif;color:var(--gold-bright);font-size:1.1rem'>💰  BUY COINS</span>",
        unsafe_allow_html=True,
    )
    user = st.session_state.user
    user_data = db.get_user(user["id"])
    if user_data is None:
        # User was deleted by admin — clear session
        st.session_state.betting_user = None
        st.session_state.user = None
        st.sidebar.warning("Your account has been removed. Please re-register.")
        st.stop()
    # Keep session state in sync with DB
    st.session_state.user = dict(user_data)
    coins = user_data["current_coins"]
    st.sidebar.caption(f"Balance: **{coins} coins**")
    vnd = st.sidebar.number_input(
        "VND", min_value=100000, value=100000, step=100000,
        key="buy_coins_sidebar_vnd",
        help="1,000 VND = 1 coin.",
    )
    est = vnd // 1000
    st.sidebar.caption(f"→ **{est} coins** ({vnd:,} VND)")

    if st.sidebar.button("Send Request  ✓", key="buy_coins_sidebar_btn", use_container_width=True):
        _purchase_confirm_dialog(user["id"], vnd, est)

    if st.session_state.get("_purchase_success"):
        st.sidebar.success(st.session_state._purchase_success)
        st.session_state.pop("_purchase_success")
        st.session_state.pop("buy_coins_sidebar_vnd", None)
        st.rerun()

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
                _render_overview_quick_bet(m)

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

    elif view == "🔒 Admin":
        admin_panel.render_admin()

except requests.exceptions.RequestException as e:
    st.error(f"API connection error: {e}")
except Exception as e:
    st.error(f"Error: {e}")
