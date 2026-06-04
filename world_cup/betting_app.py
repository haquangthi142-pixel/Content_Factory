import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import datetime

from world_cup import api as match_api
from world_cup import db
from world_cup import betting_ui

# ---------------------------------------------------------------------------
# Global theme CSS — typography, buttons, inputs, layout overrides
# Component CSS (cards, history, podium, etc.) is in betting_ui.py
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
    --shadow-elevated: 0 8px 40px rgba(0,0,0,0.55);
    --radius-sm: 8px; --radius-md: 12px; --radius-lg: 18px;
}

.stApp { background: var(--bg-deep); }
.stMainBlockContainer, .block-container { background: var(--bg-deep) !important; padding-top: 2rem !important; }
.main > .block-container { background: radial-gradient(ellipse at 50% 0%, rgba(212,168,67,0.05) 0%, transparent 65%); }

h1, h2, h3, h4 {
    font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 0.04em;
    color: var(--text-primary) !important; text-transform: uppercase;
}
h1 { font-size: 3.6rem !important; }
h2 { font-size: 2.4rem !important; }
h3 { font-size: 1.6rem !important; }

p, span, div, caption, label, .stMarkdown, .stText, li {
    font-family: 'Chakra Petch', sans-serif; color: var(--text-primary); font-size: 0.95rem;
}

.stButton > button {
    font-family: 'Chakra Petch', sans-serif !important; font-weight: 600 !important;
    font-size: 0.95rem !important; letter-spacing: 0.03em;
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border-active) !important;
    background: linear-gradient(135deg, rgba(212,168,67,0.18) 0%, rgba(212,168,67,0.06) 100%) !important;
    color: var(--gold-bright) !important; transition: all 0.2s ease;
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
    color: var(--text-muted) !important;
}

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

.stRadio [data-testid="stMarkdownContainer"] p { font-size: 1.05rem !important; }
hr { border-color: var(--border-subtle) !important; margin: 1rem 0 !important; }
[data-testid="stInfo"], [data-testid="stNotification"] {
    background: var(--bg-surface) !important; border: 1px solid var(--border-active) !important;
    border-radius: var(--radius-md) !important; color: var(--text-primary) !important;
    font-size: 0.95rem !important; padding: 1rem 1.25rem !important;
}

@media (max-width: 640px) {
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.6rem !important; }
    h3 { font-size: 1.25rem !important; }
    .podium-bar.gold { height: 110px; }
    .podium-bar.silver { height: 85px; }
    .podium-bar.bronze { height: 65px; }
    .podium-medal { font-size: 1.8rem; }
    .podium-name { font-size: 0.78rem; }
    .podium-coins { font-size: 0.9rem; }
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

if "user" not in st.session_state:
    st.session_state.user = None


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

if st.session_state.user is None:
    betting_ui.render_login_screen()
    st.stop()


# ---------------------------------------------------------------------------
# Auto-sync matches on first login (once per session)
# ---------------------------------------------------------------------------

if not st.session_state.get("_matches_synced"):
    db.sync_matches_from_api()
    st.session_state._matches_synced = True


# ---------------------------------------------------------------------------
# Main game UI (user is logged in)
# ---------------------------------------------------------------------------

user = st.session_state.user
user_data = db.get_user(user["id"])
coins = user_data["current_coins"]
leaderboard = db.get_leaderboard()
rank = next((i + 1 for i, r in enumerate(leaderboard) if r["id"] == user["id"]), "?")

betting_ui.render_game_header(user_data, coins, rank)

_, btn_col = st.columns([6, 1])
with btn_col:
    if st.button("←  Logout", key="bet_logout"):
        st.session_state.user = None
        st.rerun()

st.markdown("---")

tab_bet, tab_mybets, tab_leaderboard, tab_missions = st.tabs([
    "⚽  Place Bets", "📋  My Bets", "🏅  Leaderboard", "🎯  Missions"
])

with tab_bet:
    betting_ui.render_place_bets_tab(user["id"], coins)

with tab_mybets:
    betting_ui.render_my_bets_tab(user["id"])

with tab_leaderboard:
    betting_ui.render_leaderboard_tab()

with tab_missions:
    betting_ui.render_missions_tab(user["id"])
