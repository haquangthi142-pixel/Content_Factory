import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import datetime

from world_cup import api as match_api
from world_cup import db

# ---------------------------------------------------------------------------
# Custom CSS — Warm Stadium (friendly, large type, high readability)
# ---------------------------------------------------------------------------
BETTING_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Chakra+Petch:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-deep: #0c1118;
    --bg-surface: #161d27;
    --bg-elevated: #1c2430;
    --bg-high: #222b38;
    --gold: #d4a843;
    --gold-bright: #f0c75e;
    --gold-soft: #b8942e;
    --green-ok: #2ecc71;
    --red-live: #e74c3c;
    --orange-pending: #f39c12;
    --text-primary: #f0ede5;
    --text-secondary: #b5b3aa;
    --text-muted: #706e68;
    --border-faint: rgba(255,255,255,0.06);
    --border-subtle: rgba(255,255,255,0.10);
    --border-active: rgba(212,168,67,0.40);
    --border-glow: rgba(240,199,94,0.55);
    --shadow-card: 0 2px 16px rgba(0,0,0,0.35);
    --shadow-elevated: 0 8px 40px rgba(0,0,0,0.55);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 18px;
}

.stApp { background: var(--bg-deep); }
.stMainBlockContainer, .block-container { background: var(--bg-deep) !important; padding-top: 2rem !important; }

.main > .block-container {
    background: radial-gradient(ellipse at 50% 0%, rgba(212,168,67,0.05) 0%, transparent 65%);
}

/* ---- Typography (scaled up ~20%) ---- */
h1, h2, h3, h4 {
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: 0.04em; color: var(--text-primary) !important; text-transform: uppercase;
}
h1 { font-size: 3.6rem !important; }
h2 { font-size: 2.4rem !important; }
h3 { font-size: 1.6rem !important; }

p, span, div, caption, label, .stMarkdown, .stText, li {
    font-family: 'Chakra Petch', sans-serif; color: var(--text-primary); font-size: 0.95rem;
}

/* ---- Buttons — larger, friendlier ---- */
.stButton > button {
    font-family: 'Chakra Petch', sans-serif !important; font-weight: 600 !important;
    font-size: 0.95rem !important; letter-spacing: 0.03em;
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border-active) !important;
    background: linear-gradient(135deg, rgba(212,168,67,0.18) 0%, rgba(212,168,67,0.06) 100%) !important;
    color: var(--gold-bright) !important; transition: all 0.2s ease; cursor: pointer;
    padding: 0.55rem 1.2rem !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(212,168,67,0.28) 0%, rgba(212,168,67,0.14) 100%) !important;
    border-color: var(--border-glow) !important;
    box-shadow: 0 0 24px rgba(212,168,67,0.18); transform: translateY(-1px);
}
.stButton > button:active { transform: translateY(0); }
.stButton > button:disabled {
    opacity: 0.3; border-color: var(--border-faint) !important;
    color: var(--text-muted) !important; pointer-events: none;
}

/* ---- Metrics ---- */
[data-testid="stMetric"] {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md); padding: 1.2rem 0.9rem; text-align: center;
    box-shadow: var(--shadow-card);
}
[data-testid="stMetric"] label {
    font-family: 'Bebas Neue', sans-serif !important; font-size: 0.95rem !important;
    letter-spacing: 0.08em; color: var(--gold-bright) !important; text-transform: uppercase;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', sans-serif !important; font-size: 2.6rem !important;
    color: var(--text-primary) !important;
}

/* ---- Tabs — bigger, softer ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: var(--bg-surface); border-radius: var(--radius-md);
    padding: 5px; border: 1px solid var(--border-subtle);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Chakra Petch', sans-serif !important; font-weight: 600 !important;
    font-size: 0.95rem !important; color: var(--text-secondary) !important;
    border-radius: var(--radius-sm); padding: 0.6rem 1.3rem; transition: all 0.2s;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, var(--gold) 0%, var(--gold-soft) 100%) !important;
    color: #0c0c0c !important; box-shadow: 0 2px 10px rgba(212,168,67,0.35);
}

/* ---- Inputs — larger touch targets ---- */
.stTextInput input {
    font-family: 'Chakra Petch', sans-serif !important; font-size: 1rem !important;
    background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-sm) !important; color: var(--text-primary) !important;
    padding: 0.75rem 0.9rem !important; transition: border 0.2s;
}
.stTextInput input:focus {
    border-color: var(--border-active) !important;
    box-shadow: 0 0 0 3px rgba(212,168,67,0.12) !important;
}
.stNumberInput input {
    font-family: 'JetBrains Mono', monospace !important; font-size: 1rem !important;
    background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-sm) !important; color: var(--gold-bright) !important;
    padding: 0.75rem 0.9rem !important;
}

/* ---- Radio buttons ---- */
.stRadio [data-testid="stMarkdownContainer"] p { font-size: 1.05rem !important; }

hr { border-color: var(--border-subtle) !important; margin: 1rem 0 !important; }

[data-testid="stInfo"], [data-testid="stNotification"] {
    background: var(--bg-surface) !important; border: 1px solid var(--border-active) !important;
    border-radius: var(--radius-md) !important; color: var(--text-primary) !important;
    font-size: 0.95rem !important; padding: 1rem 1.25rem !important;
}

/* =========================================================================
   Login screen — bigger, warmer, more inviting
   ========================================================================= */
.login-card {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 3rem 2.5rem; max-width: 480px;
    margin: 0 auto; box-shadow: var(--shadow-elevated); position: relative; overflow: hidden;
}
.login-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 4px; background: linear-gradient(90deg, transparent, var(--gold-bright), transparent);
    opacity: 0.7;
}
.login-card::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(240,199,94,0.08) 0%, transparent 65%);
    pointer-events: none;
}

/* =========================================================================
   Header bar — roomier stats
   ========================================================================= */
.header-bar {
    display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 1.5rem 1.75rem; margin-bottom: 1.25rem;
    box-shadow: var(--shadow-card); position: relative;
}
.header-bar::after {
    content: ''; position: absolute; bottom: 0; left: 2.5rem; right: 2.5rem;
    height: 1px; background: linear-gradient(90deg, transparent, var(--border-active), transparent);
}
.header-bar .brand {
    font-family: 'Bebas Neue', sans-serif; font-size: 2.4rem;
    letter-spacing: 0.06em; color: var(--text-primary); margin-right: auto;
}
.header-bar .stat-box {
    text-align: center; min-width: 110px; padding: 0.5rem 1.2rem;
    background: rgba(0,0,0,0.22); border-radius: var(--radius-sm);
    border: 1px solid var(--border-faint);
}
.header-bar .stat-label {
    font-family: 'Bebas Neue', sans-serif; font-size: 0.8rem;
    letter-spacing: 0.1em; color: var(--gold-bright); text-transform: uppercase;
}
.header-bar .stat-value {
    font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem;
    color: var(--text-primary); line-height: 1;
}

/* =========================================================================
   Date group header
   ========================================================================= */
.date-header {
    display: flex; align-items: center; gap: 1rem;
    margin: 1.5rem 0 0.75rem 0; padding: 0.5rem 0;
}
.date-header .line {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-active), transparent);
}
.date-header .date-text {
    font-family: 'Bebas Neue', sans-serif; font-size: 1.5rem;
    letter-spacing: 0.06em; color: var(--gold-bright);
    white-space: nowrap; text-transform: uppercase;
}
.date-header .match-count {
    font-family: 'Chakra Petch', sans-serif; font-size: 0.85rem;
    color: var(--text-secondary); white-space: nowrap;
}

/* =========================================================================
   Match cards — fixture-list style
   ========================================================================= */
.match-fixture {
    display: flex; align-items: center; gap: 1rem;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md); padding: 1rem 1.5rem;
    margin-bottom: 0.5rem; transition: all 0.2s;
    box-shadow: var(--shadow-card); cursor: default;
}
.match-fixture:hover {
    border-color: var(--border-active); background: var(--bg-elevated);
}
.match-fixture.live {
    border-color: rgba(231,76,60,0.45);
    animation: floodlight-pulse 2.5s infinite;
}
.match-fixture.already-bet {
    border-left: 4px solid var(--green-ok);
}

@keyframes floodlight-pulse {
    0%, 100% { box-shadow: 0 0 8px rgba(231,76,60,0.12); }
    50%      { box-shadow: 0 0 22px rgba(231,76,60,0.28); }
}

/* Time column */
.match-fixture .fixture-time {
    text-align: center; min-width: 70px; flex-shrink: 0;
    border-right: 1px solid var(--border-subtle); padding-right: 1rem;
}
.match-fixture .fixture-time .time-utc {
    font-family: 'JetBrains Mono', monospace; font-size: 1.1rem;
    font-weight: 600; color: var(--text-primary); line-height: 1;
}
.match-fixture .fixture-time .time-vn {
    font-family: 'Chakra Petch', sans-serif; font-size: 0.78rem;
    color: var(--text-secondary); margin-top: 3px;
}

/* Teams column */
.match-fixture .fixture-teams {
    flex: 1; display: flex; align-items: center; gap: 0.75rem;
    min-width: 0;
}
.match-fixture .fixture-teams .team-name {
    font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 1.15rem; color: var(--text-primary); flex: 1; min-width: 0;
}
.match-fixture .fixture-teams .team-name.home { text-align: right; }
.match-fixture .fixture-teams .team-name.away { text-align: left; }
.match-fixture .fixture-teams .vs-badge {
    font-family: 'Bebas Neue', sans-serif; font-size: 0.85rem;
    padding: 4px 10px; border-radius: 4px; flex-shrink: 0;
    background: rgba(255,255,255,0.06); color: var(--text-muted);
    letter-spacing: 0.08em;
}

/* Status badge column */
.match-fixture .fixture-status {
    flex-shrink: 0; text-align: center; min-width: 75px;
}
.match-fixture .fixture-status .status-badge {
    display: inline-block; font-family: 'Chakra Petch', sans-serif;
    font-weight: 600; font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.06em; padding: 4px 12px; border-radius: 20px; color: #fff;
}
.match-fixture .fixture-status .status-badge.live-badge {
    background: var(--red-live);
    animation: badge-blink 1.5s infinite;
}
@keyframes badge-blink {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.6; }
}
.match-fixture .fixture-status .status-badge.upcoming {
    background: rgba(255,255,255,0.08); color: var(--text-secondary);
}

/* Existing bet info (replaces action column) */
.match-fixture .fixture-bet-info {
    flex-shrink: 0; text-align: right; min-width: 90px;
}
.match-fixture .fixture-bet-info .bet-choice {
    font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.9rem; color: var(--green-ok);
}
.match-fixture .fixture-bet-info .bet-amount {
    font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;
    color: var(--text-secondary); margin-top: 2px;
}

/* =========================================================================
   Betting slip
   ========================================================================= */
.bet-slip {
    background: var(--bg-high); border: 1px solid var(--border-active);
    border-radius: var(--radius-md); padding: 1.75rem 1.5rem 1.5rem 1.5rem;
    margin: 0.75rem 0 1rem 0; box-shadow: inset 0 0 40px rgba(0,0,0,0.3);
    position: relative;
}
.bet-slip::before {
    content: 'BETTING SLIP'; position: absolute; top: -12px; left: 1.25rem;
    font-family: 'Bebas Neue', sans-serif; font-size: 0.8rem;
    letter-spacing: 0.15em; color: var(--gold-bright);
    background: var(--bg-high); padding: 3px 12px;
    border: 1px solid var(--border-active); border-radius: 4px;
}

/* =========================================================================
   My Bets history — larger rows
   ========================================================================= */
.history-row {
    display: flex; justify-content: space-between; align-items: center;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md); padding: 0.9rem 1.5rem;
    margin-bottom: 0.55rem; transition: all 0.2s; box-shadow: var(--shadow-card);
}
.history-row:hover { border-color: var(--border-subtle); background: var(--bg-elevated); }
.history-row .hist-teams { font-weight: 600; font-size: 1.05rem; color: var(--text-primary); }
.history-row .hist-detail { font-size: 0.88rem; color: var(--text-secondary); margin-top: 3px; }
.hist-status {
    display: inline-block; font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em;
    padding: 4px 14px; border-radius: 20px; color: #fff;
    min-width: 75px; text-align: center;
}
.hist-date {
    font-size: 0.78rem; color: var(--text-muted); margin-top: 3px;
    font-family: 'JetBrains Mono', monospace;
}

/* =========================================================================
   Leaderboard podium
   ========================================================================= */
.podium-bar {
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    padding-top: 1.8rem; position: relative; text-align: center; flex: 1; max-width: 220px;
}
.podium-bar.gold   { background: linear-gradient(180deg, #644c00 0%, #2e1e00 100%); border: 1px solid rgba(240,199,94,0.45); height: 160px; }
.podium-bar.silver { background: linear-gradient(180deg, #444 0%, #1f1f1f 100%); border: 1px solid rgba(192,192,192,0.30); height: 125px; }
.podium-bar.bronze { background: linear-gradient(180deg, #4a2e0a 0%, #1e1100 100%); border: 1px solid rgba(205,127,50,0.40); height: 95px; }
.podium-medal { font-size: 2.6rem; margin-bottom: 0.6rem; }
.podium-name { font-family: 'Chakra Petch', sans-serif; font-weight: 700; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 0.3rem; }
.podium-coins { font-family: 'Bebas Neue', sans-serif; font-size: 1.15rem; color: var(--gold-bright); }

.leaderboard-row {
    display: flex; align-items: center; gap: 1rem;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm); padding: 0.65rem 1.25rem; margin-bottom: 0.35rem;
    transition: all 0.15s;
}
.leaderboard-row:hover { background: var(--bg-elevated); }
.leaderboard-row .lb-rank {
    font-family: 'Bebas Neue', sans-serif; font-size: 1.3rem;
    color: var(--text-muted); min-width: 34px; text-align: center;
}
.leaderboard-row .lb-name { flex: 1; font-family: 'Chakra Petch', sans-serif; font-weight: 500; font-size: 1rem; color: var(--text-primary); }
.leaderboard-row .lb-coins { font-family: 'Bebas Neue', sans-serif; font-size: 1.15rem; color: var(--gold-bright); }

/* =========================================================================
   Mission cards
   ========================================================================= */
.mission-card {
    display: flex; align-items: center;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md); padding: 1.2rem 1.5rem;
    box-shadow: var(--shadow-card); transition: all 0.2s;
}
.mission-card:hover { border-color: var(--border-subtle); background: var(--bg-elevated); }
.mission-card .mission-icon { font-size: 2.2rem; margin-right: 1.2rem; width: 52px; text-align: center; flex-shrink: 0; }
.mission-card .mission-info { flex: 1; }
.mission-card .mission-label { font-weight: 600; font-size: 1.05rem; color: var(--text-primary); }
.mission-card .mission-reward {
    font-size: 0.88rem; color: var(--gold-bright); margin-top: 3px;
    font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.04em;
}
.mission-chip {
    display: inline-block; font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em;
    padding: 7px 18px; border-radius: 20px;
}
.mission-chip.done {
    background: rgba(46,204,113,0.18); color: var(--green-ok);
    border: 1px solid rgba(46,204,113,0.35);
}

/* =========================================================================
   Utilities
   ========================================================================= */
.coin-amount { font-family: 'JetBrains Mono', monospace !important; font-weight: 500; }

/* =========================================================================
   Responsive
   ========================================================================= */
@media (max-width: 640px) {
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.6rem !important; }
    h3 { font-size: 1.25rem !important; }
    .header-bar { flex-direction: column; padding: 1.2rem; gap: 0.6rem; }
    .header-bar .brand { margin-right: 0; font-size: 1.8rem; }
    .header-bar .stat-box { min-width: 80px; }
    .header-bar .stat-value { font-size: 1.4rem; }
    .podium-bar.gold { height: 110px; }
    .podium-bar.silver { height: 85px; }
    .podium-bar.bronze { height: 65px; }
    .podium-medal { font-size: 1.8rem; }
    .podium-name { font-size: 0.78rem; }
    .podium-coins { font-size: 0.9rem; }
    .bet-match-card .match-teams { font-size: 1rem; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
}

@media (min-width: 641px) and (max-width: 1024px) {
    h1 { font-size: 2.8rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.35rem !important; }
}
"""

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
db.init_db()

st.set_page_config(
    page_title="World Cup 2026 — Internal Betting Game",
    page_icon="🏆",
    layout="wide",
)
st.markdown(f"<style>{BETTING_CSS}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login(phone: str, name: str):
    user = db.get_user_by_phone(phone)
    if not user:
        uid = db.register_user(phone, name)
        st.session_state.user = dict(db.get_user(uid))
        st.rerun()
    if user["full_name"].strip().lower() != name.strip().lower():
        st.error(f"This phone number is already registered to **{user['full_name']}**.")
        return
    st.session_state.user = dict(user)
    st.rerun()


def logout():
    st.session_state.user = None
    st.rerun()


# ---------------------------------------------------------------------------
# Login screen
# ---------------------------------------------------------------------------

if st.session_state.user is None:
    # Hero title — bigger, warmer
    st.markdown("""
    <div style="text-align:center;padding-top:3rem;">
        <h1 style="font-size:4.5rem;margin-bottom:0;background:linear-gradient(180deg, #f5d78c 0%, #c9a94e 60%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
            WORLD CUP 2026
        </h1>
        <p style="font-family:'Chakra Petch',sans-serif;color:var(--text-secondary);font-size:1.2rem;margin-top:-0.5rem;">
            Internal Betting Game
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("""
        <div class="login-card">
            <h3 style="margin-top:0;text-align:center;font-size:1.8rem;">Welcome</h3>
            <p style="text-align:center;font-size:0.95rem;color:var(--text-secondary);margin-bottom:2rem;">
                Sign in or register to start betting
            </p>
        """, unsafe_allow_html=True)

        phone = st.text_input("Phone Number", placeholder="+84xxxxxxxxx", key="login_phone")
        name = st.text_input("Full Name", placeholder="Nguyen Van A", key="login_name")
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Enter the Game  →", use_container_width=True, key="login_btn"):
            if phone.strip() and name.strip():
                login(phone.strip(), name.strip())
            else:
                st.warning("Please fill in both fields.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# ---------------------------------------------------------------------------
# Main game UI (user is logged in)
# ---------------------------------------------------------------------------

user = st.session_state.user
user_data = db.get_user(user["id"])
coins = user_data["current_coins"]
leaderboard = db.get_leaderboard()
rank = next((i + 1 for i, r in enumerate(leaderboard) if r["id"] == user["id"]), "?")

# ---- Header bar ----
rank_medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else "#"))
st.markdown(f"""
<div class="header-bar">
    <span class="brand">Betting Game</span>
    <div class="stat-box">
        <div class="stat-label">Wallet</div>
        <div class="stat-value coin-amount">{coins:,}</div>
    </div>
    <div class="stat-box">
        <div class="stat-label">Rank</div>
        <div class="stat-value">{rank_medal} {rank}</div>
    </div>
    <div class="stat-box" style="border-color:var(--border-active);">
        <div class="stat-label">Player</div>
        <div class="stat-value" style="font-size:1.1rem;font-family:'Chakra Petch',sans-serif;">{user_data['full_name']}</div>
    </div>
</div>
""", unsafe_allow_html=True)

_, btn_col = st.columns([6, 1])
with btn_col:
    if st.button("←  Logout", key="bet_logout"):
        logout()

st.markdown("---")

# ---- Tabs ----
tab_bet, tab_mybets, tab_leaderboard, tab_missions = st.tabs([
    "⚽  Place Bets", "📋  My Bets", "🏅  Leaderboard", "🎯  Missions"
])

# ===========================================================================
# Tab 1: Place Bets
# ===========================================================================
with tab_bet:
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("Upcoming & Live Matches")
    with c2:
        if st.button("🔄  Sync Matches", use_container_width=True, key="sync_btn"):
            with st.spinner("Syncing latest fixtures..."):
                n = db.sync_matches_from_api()
            st.success(f"Synced {n} matches")
            st.rerun()

    st.info("💰  **Payout:** 2× your bet on correct outcome. Bets must be in multiples of 10 coins.")

    conn = db.get_connection()
    matches = conn.execute(
        "SELECT * FROM matches WHERE status != 'Finished' ORDER BY match_time LIMIT 50"
    ).fetchall()
    conn.close()

    if not matches:
        st.info("No upcoming matches yet. Click 'Sync Matches' to load the schedule.")
    else:
        # ---- Group matches by date ----
        from collections import defaultdict
        from datetime import datetime as dt, timedelta, timezone

        VN_TZ = timezone(timedelta(hours=7))
        grouped = defaultdict(list)
        for m in matches:
            try:
                utc_str = m["match_time"].replace("Z", "+00:00")
                utc_dt = dt.fromisoformat(utc_str)
            except (ValueError, AttributeError):
                utc_dt = dt.now(timezone.utc)
            date_key = utc_dt.strftime("%Y-%m-%d")
            grouped[date_key].append((m, utc_dt))

        first_date = True
        for date_key in sorted(grouped.keys()):
            day_matches = grouped[date_key]

            # Date header
            try:
                date_obj = dt.strptime(date_key, "%Y-%m-%d")
                date_label = date_obj.strftime("%A, %d %B %Y")
            except ValueError:
                date_label = date_key

            if first_date:
                first_date = False
            else:
                st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="date-header">
                <span class="line"></span>
                <span class="date-text">{date_label}</span>
                <span class="match-count">{len(day_matches)} matches</span>
                <span class="line"></span>
            </div>
            """, unsafe_allow_html=True)

            for m, utc_dt in day_matches:
                match_id = m["match_id"]
                vn_dt = utc_dt.astimezone(VN_TZ)
                time_utc = utc_dt.strftime("%H:%M")
                time_vn = vn_dt.strftime("%H:%M")

                conn = db.get_connection()
                existing = conn.execute(
                    "SELECT * FROM bets WHERE user_id = ? AND match_id = ?",
                    (user["id"], match_id),
                ).fetchone()
                conn.close()

                is_live = m["status"] == "Live"
                card_class = "live" if is_live else ("already-bet" if existing else "")

                # Status badge
                if is_live:
                    status_html = '<span class="status-badge live-badge">● LIVE</span>'
                else:
                    status_html = '<span class="status-badge upcoming">📅 Upcoming</span>'

                if existing:
                    # Card with existing bet — all info inline, no button needed
                    bm = {"A": f"{m['team_a']} Win", "B": f"{m['team_b']} Win", "DRAW": "Draw"}
                    st.markdown(f"""
                    <div class="match-fixture {card_class}">
                        <div class="fixture-time">
                            <div class="time-utc">{time_utc}</div>
                            <div class="time-vn">{time_vn} VN</div>
                        </div>
                        <div class="fixture-teams">
                            <span class="team-name home">{m['team_a']}</span>
                            <span class="vs-badge">VS</span>
                            <span class="team-name away">{m['team_b']}</span>
                        </div>
                        <div class="fixture-status">{status_html}</div>
                        <div class="fixture-bet-info">
                            <div class="bet-choice">✓ {bm.get(existing['bet_choice'], existing['bet_choice'])}</div>
                            <div class="bet-amount">{existing['bet_amount']} coins</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                else:
                    # Card without bet — show card + action button
                    card_col, btn_col = st.columns([6, 1])
                    with card_col:
                        st.markdown(f"""
                        <div class="match-fixture {card_class}">
                            <div class="fixture-time">
                                <div class="time-utc">{time_utc}</div>
                                <div class="time-vn">{time_vn} VN</div>
                            </div>
                            <div class="fixture-teams">
                                <span class="team-name home">{m['team_a']}</span>
                                <span class="vs-badge">VS</span>
                                <span class="team-name away">{m['team_b']}</span>
                            </div>
                            <div class="fixture-status">{status_html}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with btn_col:
                        ek = f"bet_expand_{match_id}"
                        if ek not in st.session_state:
                            st.session_state[ek] = False
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Place Bet  →", key=f"btn_{match_id}", use_container_width=True):
                            st.session_state[ek] = not st.session_state[ek]
                            st.rerun()

                # Expanded betting slip
                if existing is None and st.session_state.get(f"bet_expand_{match_id}", False):
                    st.markdown('<div class="bet-slip">', unsafe_allow_html=True)

                    choice = st.radio(
                        "Pick outcome:",
                        [f"{m['team_a']} Win", "Draw", f"{m['team_b']} Win"],
                        key=f"choice_{match_id}",
                        horizontal=True,
                    )
                    choice_map = {
                        f"{m['team_a']} Win": "A",
                        "Draw": "DRAW",
                        f"{m['team_b']} Win": "B",
                    }

                    amt_key = f"amount_{match_id}"
                    if amt_key not in st.session_state:
                        st.session_state[amt_key] = 50

                    col_a, col_b, col_c = st.columns([1, 1, 1])
                    with col_a:
                        st.session_state[amt_key] = st.number_input(
                            "Bet amount",
                            min_value=10, max_value=coins, value=st.session_state[amt_key],
                            step=10, key=f"num_{match_id}",
                        )
                    with col_b:
                        for sv in [10, 50, 100]:
                            if st.button(f"+{sv}", key=f"qs_{match_id}_{sv}"):
                                st.session_state[amt_key] = min(st.session_state[amt_key] + sv, coins)
                                st.rerun()
                    with col_c:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Confirm Bet  ✓", key=f"confirm_{match_id}", use_container_width=True):
                            try:
                                db.place_bet(user["id"], match_id, choice_map[choice], st.session_state[amt_key])
                                st.success(f"Bet placed! {st.session_state[amt_key]} coins on {choice}")
                                st.session_state[f"bet_expand_{match_id}"] = False
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))

                    st.markdown('</div>', unsafe_allow_html=True)

# ===========================================================================
# Tab 2: My Bets
# ===========================================================================
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
        st.info("No bets placed yet. Head to 'Place Bets' to get started!")
    else:
        sc = {
            "Pending": "rgba(243,156,18,0.85)",
            "Won": "var(--green-ok)",
            "Lost": "var(--red-live)",
            "Refunded": "#95a5a6",
        }
        for b in my_bets:
            cd = {"A": f"{b['team_a']} Win", "B": f"{b['team_b']} Win", "DRAW": "Draw"}
            status_color = sc.get(b["status"], "gray")
            st.markdown(f"""
            <div class="history-row">
                <div>
                    <div class="hist-teams">{b['team_a']}  vs  {b['team_b']}</div>
                    <div class="hist-detail">
                        Choice: {cd.get(b['bet_choice'], b['bet_choice'])} &nbsp;·&nbsp;
                        <span class="coin-amount">{b['bet_amount']} coins</span>
                    </div>
                </div>
                <div style="text-align:right;">
                    <span class="hist-status" style="background:{status_color};">{b['status']}</span>
                    <div class="hist-date">{b['created_at'][:16]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ===========================================================================
# Tab 3: Leaderboard
# ===========================================================================
with tab_leaderboard:
    st.subheader("Company Leaderboard")

    lb = db.get_leaderboard()
    if not lb:
        st.info("No participants yet. Share the game with colleagues!")
    else:
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
                        <div class="podium-name">{row['full_name']}</div>
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
                <span class="lb-name" style="{name_style}">{row['full_name']}</span>
                <span class="lb-coins">{row['current_coins']:,}</span>
            </div>
            """, unsafe_allow_html=True)

# ===========================================================================
# Tab 4: Missions
# ===========================================================================
with tab_missions:
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
            (user["id"], mission["type"], today),
        ).fetchone()["cnt"]
        conn.close()

        card_col, action_col = st.columns([4, 1])
        with card_col:
            st.markdown(f"""
            <div class="mission-card">
                <div class="mission-icon">{mission['icon']}</div>
                <div class="mission-info">
                    <div class="mission-label">{mission['label']}</div>
                    <div class="mission-reward">+{mission['reward']} coins</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with action_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if done > 0:
                st.markdown(
                    '<span class="mission-chip done">Done ✓</span>',
                    unsafe_allow_html=True,
                )
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
                        db.complete_mission(user["id"], mission["type"], mission["reward"])
                        st.success(f"+{mission['reward']} coins!")
                        st.rerun()

        st.markdown("")
