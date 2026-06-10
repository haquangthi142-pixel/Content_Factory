"""Shared betting-game UI components. Used by app.py (embedded tab) and betting_app.py (standalone)."""

import html
import streamlit as st
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from world_cup import db
from world_cup.components import match_card_db

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

BETTING_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Chakra+Petch:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-deep: #0c1118; --bg-surface: #161d27; --bg-elevated: #1c2430;
    --bg-high: #222b38; --gold: #d4a843; --gold-bright: #f0c75e; --gold-soft: #b8942e;
    --green-ok: #2ecc71; --red-live: #e74c3c; --orange-pending: #f39c12;
    --text-primary: #f0ede5; --text-secondary: #b5b3aa; --text-muted: #706e68;
    --border-faint: rgba(255,255,255,0.06); --border-subtle: rgba(255,255,255,0.10);
    --border-active: rgba(212,168,67,0.40); --border-glow: rgba(240,199,94,0.55);
    --shadow-card: 0 2px 16px rgba(0,0,0,0.35);
}

    /* Hide default Streamlit header & footer */
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { visibility: hidden !important; }

                /* ── Login form card ── */
    [data-testid='stForm'] {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 14px !important; padding: 1.75rem 1.5rem !important;
        max-width: 380px !important; margin: 0 auto !important;
        box-shadow: 0 12px 60px rgba(0,0,0,0.65), 0 0 120px rgba(212,168,67,0.04) !important;
        animation: card-in 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
        position: relative;
    }
    @keyframes card-in {
        from { opacity: 0; transform: translateY(24px) scale(0.97); }
        to   { opacity: 1; transform: translateY(0) scale(1); }
    }
    [data-testid='stForm']::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, transparent, var(--gold-bright), transparent);
        opacity: 0.6; border-radius: 14px 14px 0 0;
    }

    [data-testid='stForm'] [data-testid='stTextInput'] input {
        background: var(--bg-deep) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
        font-family: 'Chakra Petch', sans-serif !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 0.75rem !important;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    [data-testid='stForm'] [data-testid='stTextInput'] input:focus {
        border-color: var(--border-active) !important;
        box-shadow: 0 0 0 2px rgba(212,168,67,0.12) !important;
    }
    [data-testid='stForm'] [data-testid='stTextInput'] label {
        font-family: 'Chakra Petch', sans-serif !important;
        font-size: 0.7rem !important; color: var(--text-secondary) !important;
        letter-spacing: 0.04em; text-transform: uppercase;
    }
    [data-testid='stForm'] [data-testid='stFormSubmitButton'] button {
        background: linear-gradient(135deg, #c9a94e 0%, #8b6914 100%) !important;
        border: none !important; color: #0a0e14 !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.1rem !important; letter-spacing: 0.1em !important;
        padding: 0.6rem 2rem !important; border-radius: 8px !important;
        transition: all 0.2s; text-transform: uppercase; width: 100%;
    }
    [data-testid='stForm'] [data-testid='stFormSubmitButton'] button:hover {
        background: linear-gradient(135deg, #f0c75e 0%, #c9a94e 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(212,168,67,0.35);
    }

    @media (max-height: 680px) {
        [data-testid='stForm'] { padding: 1.25rem 1.25rem !important; }
    }

.header-bar { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 1.25rem; }
.header-bar table { border-collapse: collapse; width: auto; }
.header-bar table th { font-family: 'Chakra Petch', sans-serif; font-size: 0.7rem;
    font-weight: 500; letter-spacing: 0.08em; color: var(--text-muted);
    text-transform: uppercase; padding: 2px 1.5rem 4px 0; text-align: left; }
.header-bar table td { font-family: 'JetBrains Mono', monospace; font-size: 1.2rem;
    font-weight: 600; color: var(--text-primary); padding: 0 1.5rem 0 0;
    white-space: nowrap; }
.header-bar table td.name { font-family: 'Chakra Petch', sans-serif; font-size: 1rem;
    color: var(--gold-bright); }
.header-bar table td.rank { font-size: 1rem; }
.header-bar .brand { font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem;
    letter-spacing: 0.06em; color: var(--text-primary); margin-right: auto;
    border-right: 1px solid var(--border-subtle); padding-right: 1.5rem; }

.date-header { display: flex; align-items: center; gap: 1rem; margin: 1.5rem 0 0.75rem 0; padding: 0.5rem 0; }
.date-header .line { flex: 1; height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-active), transparent); }
.date-header .date-text { font-family: 'Bebas Neue', sans-serif; font-size: 1.5rem;
    letter-spacing: 0.06em; color: var(--gold-bright); white-space: nowrap; text-transform: uppercase; }
.date-header .match-count { font-family: 'Chakra Petch', sans-serif; font-size: 0.85rem; color: var(--text-secondary); }

.match-fixture { display: flex; align-items: center; gap: 1rem;
    background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px;
    padding: 1rem 1.5rem; margin-bottom: 0.5rem; transition: all 0.2s; box-shadow: var(--shadow-card); }
.match-fixture:hover { border-color: var(--border-active); background: var(--bg-elevated); }
.match-fixture.live { border-color: rgba(231,76,60,0.45); animation: floodlight-pulse 2.5s infinite; }
.match-fixture.already-bet { border-left: 4px solid var(--green-ok); }
@keyframes floodlight-pulse {
    0%, 100% { box-shadow: 0 0 8px rgba(231,76,60,0.12); }
    50% { box-shadow: 0 0 22px rgba(231,76,60,0.28); }
}
.match-fixture .fixture-time { text-align: center; min-width: 70px; flex-shrink: 0;
    border-right: 1px solid var(--border-subtle); padding-right: 1rem; }
.match-fixture .fixture-time .time-utc { font-family: 'JetBrains Mono', monospace; font-size: 1.1rem;
    font-weight: 600; color: var(--text-primary); line-height: 1; }
.match-fixture .fixture-time .time-vn { font-family: 'Chakra Petch', sans-serif; font-size: 0.78rem;
    color: var(--text-secondary); margin-top: 3px; }
.match-fixture .fixture-teams { flex: 1; display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
.match-fixture .fixture-teams .team-name { font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 1.15rem; color: var(--text-primary); flex: 1; min-width: 0; }
.match-fixture .fixture-teams .team-name.home { text-align: right; }
.match-fixture .fixture-teams .team-name.away { text-align: left; }
.match-fixture .fixture-teams .vs-badge { font-family: 'Bebas Neue', sans-serif; font-size: 0.85rem;
    padding: 4px 10px; border-radius: 4px; flex-shrink: 0;
    background: rgba(255,255,255,0.06); color: var(--text-muted); letter-spacing: 0.08em; }
.match-fixture .fixture-bet-info { flex-shrink: 0; text-align: right; min-width: 90px; }
.match-fixture .fixture-bet-info .bet-choice { font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.9rem; color: var(--green-ok); }
.match-fixture .fixture-bet-info .bet-amount { font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;
    color: var(--text-secondary); margin-top: 2px; }
.status-badge { font-family: 'Chakra Petch', sans-serif; font-weight: 600; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.06em; padding: 4px 12px; border-radius: 20px; color: #fff; }
.status-badge.live-badge { background: var(--red-live); animation: badge-blink 1.5s infinite; }
@keyframes badge-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
.status-badge.upcoming-badge { background: rgba(255,255,255,0.08); color: var(--text-secondary); }

.bet-slip { background: var(--bg-high); border: 1px solid var(--border-active);
    border-radius: 12px; padding: 1.75rem 1.5rem 1.5rem; margin: 0.75rem 0 1rem;
    box-shadow: inset 0 0 40px rgba(0,0,0,0.3); position: relative; }
.bet-slip::before { content: 'BETTING SLIP'; position: absolute; top: -12px; left: 1.25rem;
    font-family: 'Bebas Neue', sans-serif; font-size: 0.8rem; letter-spacing: 0.15em;
    color: var(--gold-bright); background: var(--bg-high); padding: 3px 12px;
    border: 1px solid var(--border-active); border-radius: 4px; }

.history-row { display: flex; justify-content: space-between; align-items: center;
    background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px;
    padding: 0.9rem 1.5rem; margin-bottom: 0.55rem; transition: all 0.2s; box-shadow: var(--shadow-card); }
.history-row:hover { border-color: var(--border-subtle); background: var(--bg-elevated); }
.history-row .hist-teams { font-weight: 600; font-size: 1.05rem; color: var(--text-primary); }
.history-row .hist-detail { font-size: 0.88rem; color: var(--text-secondary); margin-top: 3px; }
.hist-status { display: inline-block; font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 4px 14px;
    border-radius: 20px; color: #fff; min-width: 75px; text-align: center; }
.hist-date { font-size: 0.78rem; color: var(--text-muted); margin-top: 3px; font-family: 'JetBrains Mono', monospace; }

.podium-bar { border-radius: 8px 8px 0 0; padding-top: 1.8rem; position: relative;
    text-align: center; flex: 1; max-width: 220px; }
.podium-bar.gold { background: linear-gradient(180deg, #644c00 0%, #2e1e00 100%);
    border: 1px solid rgba(240,199,94,0.45); height: 160px; }
.podium-bar.silver { background: linear-gradient(180deg, #444 0%, #1f1f1f 100%);
    border: 1px solid rgba(192,192,192,0.30); height: 125px; }
.podium-bar.bronze { background: linear-gradient(180deg, #4a2e0a 0%, #1e1100 100%);
    border: 1px solid rgba(205,127,50,0.40); height: 95px; }
.podium-medal { font-size: 2.6rem; margin-bottom: 0.6rem; }
.podium-name { font-family: 'Chakra Petch', sans-serif; font-weight: 700; font-size: 0.95rem;
    color: var(--text-primary); margin-bottom: 0.3rem; }
.podium-coins { font-family: 'Bebas Neue', sans-serif; font-size: 1.15rem; color: var(--gold-bright); }

.leaderboard-row { display: flex; align-items: center; gap: 1rem;
    background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;
    padding: 0.65rem 1.25rem; margin-bottom: 0.35rem; transition: all 0.15s; }
.leaderboard-row:hover { background: var(--bg-elevated); }
.leaderboard-row .lb-rank { font-family: 'Bebas Neue', sans-serif; font-size: 1.3rem;
    color: var(--text-muted); min-width: 34px; text-align: center; }
.leaderboard-row .lb-name { flex: 1; font-family: 'Chakra Petch', sans-serif; font-weight: 500;
    font-size: 1rem; color: var(--text-primary); }
.leaderboard-row .lb-coins { font-family: 'Bebas Neue', sans-serif; font-size: 1.15rem; color: var(--gold-bright); }

.mission-card { display: flex; align-items: center;
    background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px;
    padding: 1.2rem 1.5rem; box-shadow: var(--shadow-card); transition: all 0.2s; }
.mission-card:hover { border-color: var(--border-subtle); background: var(--bg-elevated); }
.mission-card .mission-icon { font-size: 2.2rem; margin-right: 1.2rem; width: 52px;
    text-align: center; flex-shrink: 0; }
.mission-card .mission-info { flex: 1; }
.mission-card .mission-label { font-weight: 600; font-size: 1.05rem; color: var(--text-primary); }
.mission-chip { display: inline-block; font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 7px 18px; border-radius: 20px; }
.mission-chip.done { background: rgba(46,204,113,0.18); color: var(--green-ok);
    border: 1px solid rgba(46,204,113,0.35); }
.coin-amount { font-family: 'JetBrains Mono', monospace !important; font-weight: 500; }

@media (max-width: 640px) {
    .header-bar { flex-direction: column; padding: 0.8rem; gap: 0.5rem; }
    .header-bar .brand { margin-right: 0; font-size: 1.4rem; border-right: none; padding-right: 0; }
    .header-bar table th { padding: 2px 0.8rem 2px 0; font-size: 0.65rem; }
    .header-bar table td { padding: 0 0.8rem 0 0; font-size: 1rem; }
    .podium-bar.gold { height: 110px; }
    .podium-bar.silver { height: 85px; }
    .podium-bar.bronze { height: 65px; }
}
"""

VN_TZ = timezone(timedelta(hours=7))


def _inject_css():
    """Inject betting CSS once per session."""
    if "_betting_css_injected" not in st.session_state:
        st.markdown(f"<style>{BETTING_CSS}</style>", unsafe_allow_html=True)
        st.session_state._betting_css_injected = True


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def render_login_screen():
    _inject_css()
    with st.form("login_form"):
        phone = st.text_input("Phone Number", placeholder="+84xxxxxxxxx", key="login_phone")
        name = st.text_input("Full Name", placeholder="Nguyen Van A", key="login_name")
        password = st.text_input("Password", type="password", placeholder="Min 4 characters", key="login_password")
        submitted = st.form_submit_button("Enter the Game  →", use_container_width=True)

        if submitted:
            if not (phone.strip() and name.strip() and password.strip()):
                st.warning("Please fill in all fields.")
            elif len(password.strip()) < 4:
                st.warning("Password must be at least 4 characters.")
            elif not db.check_login_rate_limit(phone.strip()):
                st.error("Too many failed attempts. Try again in a minute.")
            else:
                user = db.get_user_by_phone(phone.strip())
                if not user:
                    # New user: register with password
                    uid = db.register_user(phone.strip(), name.strip(), password.strip())
                    st.session_state.user = dict(db.get_user(uid))
                    st.rerun()
                elif user["full_name"].strip().lower() != name.strip().lower():
                    db.record_failed_login(phone.strip())
                    st.error(f"This phone number is already registered to **{user['full_name']}**.")
                elif user["password_hash"] is None:
                    # Existing user without password: set password now
                    conn = db.get_connection()
                    try:
                        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                                     (db.hash_password(password.strip()), user["id"]))
                        conn.commit()
                    finally:
                        conn.close()
                    st.session_state.user = dict(db.get_user(user["id"]))
                    st.success("Password set! Welcome back.")
                    st.rerun()
                elif db.verify_password(password.strip(), user["password_hash"]):
                    st.session_state.user = dict(user)
                    st.rerun()
                else:
                    db.record_failed_login(phone.strip())
                    st.error("Wrong password. Try again.")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_game_header(user_data: dict, coins: int, rank):
    _inject_css()
    rank_medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else "#"))
    rank_text = "#1" if rank == 1 else (f"#{rank}" if rank != "?" else "—")
    st.markdown(f"""
    <div class="header-bar">
        <span class="brand">🏆 Betting Game</span>
        <table>
            <tr>
                <th>Wallet</th>
                <th>Rank</th>
                <th>Player</th>
            </tr>
            <tr>
                <td>{coins:,}</td>
                <td class="rank">{rank_medal} {rank_text}</td>
                <td class="name">{html.escape(user_data['full_name'])}</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Place Bets
# ---------------------------------------------------------------------------

_PAGE_SIZE = 5  # matches per page


def render_place_bets_tab(user_id: int, coins: int):
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("Upcoming & Live Matches")
    with c2:
        if st.button("🔄  Sync Matches", use_container_width=True, key="sync_btn"):
            if not db.check_sync_rate_limit(user_id):
                st.warning("Please wait 30 seconds between syncs.")
            else:
                with st.spinner("Syncing latest fixtures..."):
                    n = db.sync_matches_from_api()
                st.success(f"Synced {n} matches")
                st.rerun()

    conn = db.get_connection()
    all_matches = conn.execute(
        "SELECT * FROM matches WHERE status != 'Finished' ORDER BY match_time"
    ).fetchall()
    conn.close()

    if not all_matches:
        st.info("No upcoming matches yet. Click 'Sync Matches' to load the schedule.")
        return

    # Flatten + parse times
    flat = []
    for m in all_matches:
        try:
            utc_str = m["match_time"].replace("Z", "+00:00")
            utc_dt = datetime.fromisoformat(utc_str)
        except (ValueError, AttributeError):
            utc_dt = datetime.now(timezone.utc)
        flat.append((m, utc_dt))

    total = len(flat)
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page_key = "betting_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    page = st.session_state[page_key]

    # Clamp page if matches changed
    if page > total_pages:
        page = total_pages
        st.session_state[page_key] = page

    start = (page - 1) * _PAGE_SIZE
    end = start + _PAGE_SIZE
    page_matches = flat[start:end]

    # Pagination controls (top)
    _render_pagination(page, total_pages, total, page_key, "top")

    # Group visible matches by date
    grouped = defaultdict(list)
    for m, utc_dt in page_matches:
        date_key = utc_dt.strftime("%Y-%m-%d")
        grouped[date_key].append((m, utc_dt))

    for date_key in sorted(grouped.keys()):
        day_matches = grouped[date_key]
        try:
            date_obj = datetime.strptime(date_key, "%Y-%m-%d")
            date_label = date_obj.strftime("%A, %d %B %Y")
        except ValueError:
            date_label = date_key

        st.markdown(f"""
        <div class="date-header">
            <span class="line"></span>
            <span class="date-text">{date_label}</span>
            <span class="match-count">{len(day_matches)} match(es)</span>
            <span class="line"></span>
        </div>
        """, unsafe_allow_html=True)

        for m, utc_dt in day_matches:
            _render_match_fixture(m, user_id, coins)

    # Pagination controls (bottom)
    _render_pagination(page, total_pages, total, page_key, "bottom")


def _render_pagination(page, total_pages, total, key, pos):
    """Render prev/next pagination bar."""
    prev_key = f"{key}_{pos}_prev"
    next_key = f"{key}_{pos}_next"
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.button("← Prev", key=prev_key, disabled=(page == 1),
                  on_click=lambda: st.session_state.update({key: page - 1}),
                  use_container_width=True)
    with c2:
        st.markdown(
            f"<div style='text-align:center;padding-top:6px;color:var(--text-muted);"
            f"font-family:Chakra Petch,sans-serif;font-size:0.85rem'>"
            f"Page {page} of {total_pages} &nbsp;·&nbsp; {total} matches</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.button("Next →", key=next_key, disabled=(page == total_pages),
                  on_click=lambda: st.session_state.update({key: page + 1}),
                  use_container_width=True)


def _render_existing_bets(bets: list, m: dict):
    """Render a compact list of the user's existing bets on this match."""
    sc = {"Pending": "rgba(243,156,18,0.85)", "Won": "#2ecc71",
          "Lost": "#e74c3c", "Refunded": "#95a5a6"}

    rows = []
    for b in bets:
        if b["market"] == "handicap":
            hl = b["handicap_line"]
            fav = m["team_a"] if m["handicap_favorite"] == "A" else m["team_b"]
            und = m["team_b"] if m["handicap_favorite"] == "A" else m["team_a"]
            if b["handicap_side"] == "favorite":
                choice = f"{fav} −{hl}"
            else:
                choice = f"{und} +{hl}"
        else:
            cd = {"A": f"{m['team_a']} Win", "B": f"{m['team_b']} Win", "DRAW": "Draw"}
            choice = f"1X2 · {cd.get(b['bet_choice'], b['bet_choice'])}"

        s_color = sc.get(b["status"], "gray")
        rows.append(
            f"<tr><td style='padding:3px 8px 3px 0;'>#{b['bet_id']}</td>"
            f"<td style='padding:3px 8px;'>{choice}</td>"
            f"<td style='padding:3px 8px;font-family:JetBrains Mono,monospace;text-align:right;'>{b['bet_amount']:,} coins</td>"
            f"<td style='padding:3px 0 3px 8px;text-align:right;'>"
            f"<span style='display:inline-block;font-size:0.7rem;padding:2px 10px;border-radius:10px;background:{s_color};color:#fff;'>{b['status']}</span></td></tr>"
        )

    st.markdown(f"""
    <div style="flex-basis:100%;padding:0.5rem 0;margin-top:0.25rem;border-top:1px solid var(--border-subtle);">
        <span style="font-family:'Chakra Petch',sans-serif;font-size:0.8rem;color:var(--text-secondary);">Your bets:</span>
        <table style="width:100%;font-family:'Chakra Petch',sans-serif;font-size:0.82rem;color:var(--text-primary);margin-top:4px;">
            {''.join(rows)}
        </table>
    </div>
    """, unsafe_allow_html=True)


def _render_match_fixture(m: dict, user_id: int, coins: int):
    match_id = m["match_id"]

    conn = db.get_connection()
    existing_bets = conn.execute(
        "SELECT * FROM bets WHERE user_id = ? AND match_id = ? ORDER BY created_at",
        (user_id, match_id),
    ).fetchall()
    conn.close()

    # Render match card using same style as Overview tab
    match_card_db(dict(m))

    # Show existing bets inline
    if existing_bets:
        _render_existing_bets(existing_bets, m)

    # "Bet" button
    btn_col1, btn_col2 = st.columns([5, 1])
    with btn_col2:
        ek = f"bet_expand_{match_id}"
        if ek not in st.session_state:
            st.session_state[ek] = False
        if st.button("Bet  →", key=f"btn_{match_id}", use_container_width=True):
            st.session_state[ek] = not st.session_state[ek]
            st.rerun()

    # Expanded bet slip
    if st.session_state.get(f"bet_expand_{match_id}", False):
        has_handicap = m["handicap_line"] is not None and m["handicap_favorite"] is not None
        if has_handicap:
            market_key = f"market_{match_id}"
            if market_key not in st.session_state:
                st.session_state[market_key] = "1X2"
            market_choice = st.radio(
                "Select Market:",
                ["1X2 (Win/Draw/Win)", "Handicap"],
                key=market_key,
                horizontal=True,
            )
            is_handicap = market_choice.startswith("Handicap")
        else:
            is_handicap = False

        if is_handicap:
            _render_handicap_bet_slip = globals().get("_render_handicap_bet_slip")
            if _render_handicap_bet_slip:
                _render_handicap_bet_slip(m, coins, match_id)
            else:
                st.info("Handicap betting coming soon.")
        else:
            _render_bet_slip(m, coins, match_id)


def _render_bet_slip(m: dict, coins: int, match_id: int):
    st.markdown('<div class="bet-slip">', unsafe_allow_html=True)

    if coins < 10:
        st.error("Insufficient coins. Minimum bet is 10 coins. Buy more coins or contact admin.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    choice = st.radio(
        "",
        [f"{m['team_a']} Win", "Draw", f"{m['team_b']} Win"],
        key=f"choice_{match_id}",
        horizontal=True,
    )
    choice_map = {f"{m['team_a']} Win": "A", "Draw": "DRAW", f"{m['team_b']} Win": "B"}

    num_key = f"num_{match_id}"
    if num_key not in st.session_state:
        st.session_state[num_key] = min(50, coins)

    st.caption("Quick add:")
    qc1, qc2, qc3, qc4 = st.columns([1, 1, 1, 2])
    with qc1:
        if st.button("+10", key=f"qs_{match_id}_10", use_container_width=True):
            st.session_state[num_key] = min(st.session_state[num_key] + 10, coins)
            st.rerun()
    with qc2:
        if st.button("+50", key=f"qs_{match_id}_50", use_container_width=True):
            st.session_state[num_key] = min(st.session_state[num_key] + 50, coins)
            st.rerun()
    with qc3:
        if st.button("+100", key=f"qs_{match_id}_100", use_container_width=True):
            st.session_state[num_key] = min(st.session_state[num_key] + 100, coins)
            st.rerun()
    with qc4:
        amount = st.number_input(
            "Amount", min_value=10, max_value=coins,
            step=10, key=num_key,
            label_visibility="collapsed",
        )

    if st.button("Confirm Bet  ✓", key=f"confirm_{match_id}", use_container_width=True):
        try:
            db.place_bet(st.session_state.user["id"], match_id, choice_map[choice], amount)
            st.success(f"Bet placed! {amount} coins on {choice}")
            st.session_state[f"bet_expand_{match_id}"] = False
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    st.markdown('</div>', unsafe_allow_html=True)


def _render_handicap_bet_slip(m: dict, coins: int, match_id: int):
    """Handicap betting form: pick side, amount, confirm."""
    line = m["handicap_line"]
    fav_team = m["team_a"] if m["handicap_favorite"] == "A" else m["team_b"]
    und_team = m["team_b"] if m["handicap_favorite"] == "A" else m["team_a"]
    fee = m.get("handicap_fee") or 5

    st.markdown('<div class="bet-slip">', unsafe_allow_html=True)

    if coins < 10:
        st.error("Insufficient coins. Minimum bet is 10 coins. Buy more coins or contact admin.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    st.caption(
        f"**{fav_team} −{line}**  ·  **{und_team} +{line}**  ·  "
        f"Payout: 2× − {fee}% fee"
    )

    side = st.radio(
        "Pick side:",
        [f"{fav_team} −{line}", f"{und_team} +{line}"],
        key=f"hc_side_{match_id}",
        horizontal=True,
    )
    side_code = "favorite" if side.startswith(fav_team) else "underdog"

    num_key = f"hc_num_{match_id}"
    if num_key not in st.session_state:
        st.session_state[num_key] = min(50, coins)

    st.caption("Quick add:")
    qc1, qc2, qc3, qc4 = st.columns([1, 1, 1, 2])
    with qc1:
        if st.button("+10", key=f"hc_qs_{match_id}_10", use_container_width=True):
            st.session_state[num_key] = min(st.session_state[num_key] + 10, coins)
            st.rerun()
    with qc2:
        if st.button("+50", key=f"hc_qs_{match_id}_50", use_container_width=True):
            st.session_state[num_key] = min(st.session_state[num_key] + 50, coins)
            st.rerun()
    with qc3:
        if st.button("+100", key=f"hc_qs_{match_id}_100", use_container_width=True):
            st.session_state[num_key] = min(st.session_state[num_key] + 100, coins)
            st.rerun()
    with qc4:
        amount = st.number_input(
            "Amount", min_value=10, max_value=coins,
            step=10, key=num_key,
            label_visibility="collapsed",
        )

    if st.button("Confirm Bet  ✓", key=f"hc_confirm_{match_id}", use_container_width=True):
        try:
            db.place_handicap_bet(
                st.session_state.user["id"], match_id, side_code,
                amount, line, fee,
            )
            st.success(f"Handicap bet placed! {amount} coins on {side}")
            st.session_state[f"bet_expand_{match_id}"] = False
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# My Bets
# ---------------------------------------------------------------------------

def render_my_bets_tab(user_id: int):
    st.subheader("My Betting History")
    conn = db.get_connection()
    my_bets = conn.execute(
        """SELECT b.*, m.team_a, m.team_b, m.match_time, m.status as match_status, m.result,
                  m.handicap_favorite
           FROM bets b JOIN matches m ON b.match_id = m.match_id
           WHERE b.user_id = ? ORDER BY b.created_at DESC LIMIT 50""",
        (user_id,),
    ).fetchall()
    conn.close()

    if not my_bets:
        st.info("No bets placed yet. Head to 'Place Bets' to get started!")
        return

    sc = {"Pending": "rgba(243,156,18,0.85)", "Won": "var(--green-ok)",
          "Lost": "var(--red-live)", "Refunded": "#95a5a6"}
    for b in my_bets:
        if b["market"] == "handicap":
            hl = b["handicap_line"]
            fav = b["team_a"] if b["handicap_favorite"] == "A" else b["team_b"]
            und = b["team_b"] if b["handicap_favorite"] == "A" else b["team_a"]
            if b["handicap_side"] == "favorite":
                choice_str = f"{fav} −{hl}"
            else:
                choice_str = f"{und} +{hl}"
        else:
            cd = {"A": f"{b['team_a']} Win", "B": f"{b['team_b']} Win", "DRAW": "Draw"}
            choice_str = cd[b['bet_choice']] if b['bet_choice'] in cd else b['bet_choice']
        status_color = sc.get(b["status"], "gray")
        st.markdown(f"""
        <div class="history-row">
            <div>
                <div class="hist-teams">{html.escape(b['team_a'])}  vs  {html.escape(b['team_b'])}</div>
                <div class="hist-detail">
                    Choice: {choice_str} &nbsp;·&nbsp;
                    <span class="coin-amount">{b['bet_amount']} coins</span>
                </div>
            </div>
            <div style="text-align:right;">
                <span class="hist-status" style="background:{status_color};">{b['status']}</span>
                <div class="hist-date">{b['created_at'][:16]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def render_leaderboard_tab():
    st.subheader("Company Leaderboard")
    lb = db.get_leaderboard()
    if not lb:
        st.info("No participants yet. Share the game with colleagues!")
        return

    top3 = lb[:3]
    if len(top3) >= 3:
        medals = [("🥇", "gold"), ("🥈", "silver"), ("🥉", "bronze")]
        podium_cols = st.columns([1, 1, 1])
        order = [1, 0, 2]
        for idx, col in zip(order, podium_cols):
            with col:
                row = top3[idx]
                medal, tier = medals[idx]
                st.markdown(f"""
                <div class="podium-bar {tier}">
                    <div class="podium-medal">{medal}</div>
                    <div class="podium-name">{html.escape(row['full_name'])}</div>
                    <div class="podium-coins">{row['current_coins']:,} coins</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    for i, row in enumerate(lb):
        is_top3 = i < 3
        extra_style = 'border-color:var(--border-active);' if is_top3 else ''
        rank_style = 'color:var(--gold-bright);' if is_top3 else ''
        name_style = 'font-weight:700;' if is_top3 else ''
        st.markdown(f"""
        <div class="leaderboard-row" style="{extra_style}">
            <span class="lb-rank" style="{rank_style}">{i + 1}</span>
            <span class="lb-name" style="{name_style}">{html.escape(row['full_name'])}</span>
            <span class="lb-coins">{row['current_coins']:,}</span>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

def render_missions_tab(user_id: int):
    st.subheader("Daily Missions  —  Earn Extra Coins")
    missions = [
        {"type": "share_facebook", "label": "Share match schedule on Facebook", "reward": 50, "icon": "📢"},
        {"type": "daily_login", "label": "Daily check-in", "reward": 20, "icon": "🔔"},
        {"type": "invite_friend", "label": "Invite a colleague to join", "reward": 100, "icon": "👥"},
    ]

    for mission in missions:
        conn = db.get_connection()
        today = datetime.now().strftime("%Y-%m-%d")
        done = conn.execute(
            """SELECT COUNT(*) as cnt FROM mission_logs
               WHERE user_id = ? AND mission_type = ? AND DATE(completed_at) = ?""",
            (user_id, mission["type"], today),
        ).fetchone()["cnt"]
        conn.close()

        card_col, action_col = st.columns([4, 1])
        with card_col:
            st.markdown(f"""
            <div class="mission-card">
                <div class="mission-icon">{mission['icon']}</div>
                <div class="mission-info">
                    <div class="mission-label">{mission['label']}</div>
                    <div style="font-size:0.88rem;color:var(--gold-bright);margin-top:3px;font-family:'Bebas Neue',sans-serif;">
                        +{mission['reward']} coins</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with action_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if done > 0:
                st.markdown('<span class="mission-chip done">Done ✓</span>', unsafe_allow_html=True)
            else:
                btn_label = "Share" if mission["type"] == "share_facebook" else "Claim"
                if st.button(btn_label, key=f"mission_{mission['type']}", use_container_width=True):
                    if mission["type"] == "share_facebook":
                        share_url = "https://www.facebook.com/sharer/sharer.php?u=https://www.fifa.com/worldcup"
                        st.markdown(
                            f"<a href='{share_url}' target='_blank' style='color:var(--gold-bright);font-size:1rem;'>Click here to share</a>, "
                            "then come back and click Claim again.",
                            unsafe_allow_html=True,
                        )
                    else:
                        db.complete_mission(user_id, mission["type"], mission["reward"])
                        st.success(f"+{mission['reward']} coins!")
                        st.rerun()
        st.markdown("")
