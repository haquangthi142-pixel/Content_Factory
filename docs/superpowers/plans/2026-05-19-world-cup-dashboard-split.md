# World Cup Dashboard — Front-End / Back-End Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `world_cup_dashboard.py` (766-line monolithic Streamlit app) into a three-module `world_cup/` package with clean separation between data fetching, UI rendering, and orchestration.

**Architecture:** `api.py` (data layer, zero Streamlit) → `components.py` (UI renderers, Streamlit-dependent) → `app.py` (orchestration with caching, routing, pagination). A thin `world_cup_dashboard.py` launcher stays at repo root.

**Tech Stack:** Python 3.10+, Streamlit, requests, python-dotenv

---

## File Structure

```
content_factory/
├── .env                              # NEW — API key (from hardcoded value in current file)
├── world_cup/
│   ├── __init__.py                   # NEW — empty
│   ├── api.py                        # NEW — data fetchers, no Streamlit
│   ├── components.py                 # NEW — CSS + UI renderers
│   └── app.py                        # NEW — orchestration (caching, sidebar, routing)
├── world_cup_dashboard.py            # REPLACE — becomes launcher
├── premier_league_dashboard.py       # UNCHANGED
└── requirements.txt                  # UNCHANGED (python-dotenv already listed)
```

---

### Task 1: Create `.env` with API key

**Files:**
- Create: `.env`
- Modify: `.env.example`

**Rationale:** The current API key is hardcoded on line 10. Move it to `.env` (gitignored) so `api.py` can load it via `python-dotenv`. Also update `.env.example` to document the required key name.

- [ ] **Step 1: Write `.env`**

Create `D:\Python\content_factory\.env`:

```
API_FOOTBALL_KEY=63e28e6d354043cda2975002d22f2b52
```

- [ ] **Step 2: Update `.env.example`**

Replace the current contents of `.env.example` (currently just `API_FOOTBALL_KEY=your_key_here`) with the football-data.org key name:

```
API_FOOTBALL_KEY=your_key_here
```

---

### Task 2: Create `world_cup/__init__.py`

**Files:**
- Create: `world_cup/__init__.py`

- [ ] **Step 1: Create empty init file**

Save `D:\Python\content_factory\world_cup\__init__.py` with empty content (touch equivalent).

---

### Task 3: Create `world_cup/api.py` — data layer

**Files:**
- Create: `world_cup/api.py`

**Rationale:** Extract the API client and fetchers from the original file (lines 10-49). Remove `@st.cache_data` decorators. Move API key to env var. No Streamlit dependency — this module is testable with plain Python.

- [ ] **Step 1: Write `world_cup/api.py`**

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}
COMPETITION_CODE = "WC"
SEASON = 2026


def api_get(endpoint: str, params: dict | None = None) -> dict:
    if params is None:
        params = {}
    url = f"{BASE_URL}{endpoint}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_matches():
    return api_get(
        f"/competitions/{COMPETITION_CODE}/matches", {"season": SEASON}
    )


def fetch_standings():
    return api_get(
        f"/competitions/{COMPETITION_CODE}/standings", {"season": SEASON}
    )


def fetch_teams():
    return api_get(
        f"/competitions/{COMPETITION_CODE}/teams", {"season": SEASON}
    )


def fetch_group_standings():
    data = fetch_standings()
    groups = {}
    if "standings" in data:
        for group in data["standings"]:
            group_name = (group.get("group") or "Unknown").replace(
                "GROUP_", "Group "
            )
            groups[group_name] = group["table"]
    return groups
```

---

### Task 4: Create `world_cup/components.py` — UI layer

**Files:**
- Create: `world_cup/components.py`

**Rationale:** Extract CSS and UI renderers from the original file (lines 56-543). Every function receives data as arguments — they never call the API. This is a pure extraction; no internal logic changes.

- [ ] **Step 1: Write `world_cup/components.py`**

```python
import streamlit as st
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Global CSS injection
# ---------------------------------------------------------------------------

GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Chakra+Petch:wght@300;400;500;600;700&display=swap');

/* ── Root overrides ── */
:root {
    --bg-deep: #0a0e14;
    --bg-card: #111820;
    --bg-card-hover: #161e2a;
    --gold: #d4a843;
    --gold-bright: #f0c75e;
    --gold-dim: #8b6914;
    --pitch: #0d3b0f;
    --pitch-light: #1a5c1a;
    --text-primary: #e8e4dc;
    --text-muted: #8b8d92;
    --accent-live: #e67e22;
    --accent-done: #27ae60;
    --accent-danger: #e74c3c;
    --border-subtle: rgba(255,255,255,0.06);
    --border-gold: rgba(212,168,67,0.3);
}

/* ── Streamlit chrome overrides ── */
.stApp {
    background: var(--bg-deep);
}

.stMainBlockContainer, .block-container {
    background: var(--bg-deep) !important;
}

section[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid var(--border-gold);
}

section[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
    font-family: 'Chakra Petch', sans-serif;
}

section[data-testid="stSidebar"] .stRadio label {
    font-size: 1rem;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    transition: all 0.2s;
}

section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(212,168,67,0.1);
}

/* ── Typography ── */
h1, h2, h3, h4 {
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: 0.04em;
    color: var(--text-primary) !important;
}

h1 { font-size: 2.8rem !important; }
h2 { font-size: 2rem !important; }
h3 { font-size: 1.5rem !important; }

p, span, div, caption, label, .stMarkdown, .stText {
    font-family: 'Chakra Petch', sans-serif;
    color: var(--text-primary);
}

/* ── Metric cards (scoreboard style) ── */
[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border-gold);
    border-radius: 12px;
    padding: 1.25rem 1rem;
    text-align: center;
}
[data-testid="stMetric"] label {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1rem !important;
    letter-spacing: 0.06em;
    color: var(--gold) !important;
    text-transform: uppercase;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 2.6rem !important;
    color: var(--text-primary) !important;
}

/* ── Buttons ── */
.stButton button {
    font-family: 'Chakra Petch', sans-serif !important;
    font-weight: 600;
    border-radius: 8px;
    border: 1px solid var(--border-gold) !important;
    background: var(--bg-card) !important;
    color: var(--gold-bright) !important;
    transition: all 0.2s;
}
.stButton button:hover {
    background: var(--bg-card-hover) !important;
    border-color: var(--gold-bright) !important;
}
.stButton button:disabled {
    opacity: 0.35;
    border-color: var(--border-subtle) !important;
    color: var(--text-muted) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--bg-card);
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Chakra Petch', sans-serif !important;
    font-weight: 600;
    color: var(--text-muted) !important;
    border-radius: 8px;
    padding: 0.5rem 1.2rem;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--gold) !important;
    color: #0a0e14 !important;
}

/* ── Horizontal rule ── */
hr {
    border-color: var(--border-subtle) !important;
    margin: 0.5rem 0 !important;
}

/* ── Info / error boxes ── */
[data-testid="stInfo"], [data-testid="stNotification"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-gold) !important;
    border-radius: 10px;
    color: var(--text-primary) !important;
}

/* ═══════════════════════════════════════════════════════════════
   MATCH CARD
   ═══════════════════════════════════════════════════════════════ */
.match-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    transition: all 0.25s;
    position: relative;
    overflow: hidden;
}
.match-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--gold-dim);
    border-radius: 0 3px 3px 0;
}
.match-card:hover {
    border-color: var(--border-gold);
    background: var(--bg-card-hover);
}
.match-card.live {
    border-color: rgba(230,126,34,0.5);
    animation: livePulse 2s infinite;
}
.match-card.live::before {
    background: var(--accent-live);
}
@keyframes livePulse {
    0%, 100% { box-shadow: 0 0 8px rgba(230,126,34,0.15); }
    50%      { box-shadow: 0 0 20px rgba(230,126,34,0.35); }
}

/* Date badge — the highlighted element the user asked for */
.match-date-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #1a3a1a 0%, #0d2b0d 100%);
    border: 1px solid var(--gold-dim);
    border-radius: 20px;
    padding: 4px 14px;
    margin-bottom: 10px;
    font-family: 'Chakra Petch', sans-serif;
    font-weight: 600;
    font-size: 0.8rem;
    color: var(--gold-bright);
    letter-spacing: 0.04em;
}
.match-date-big {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.35rem;
    color: var(--gold-bright);
    letter-spacing: 0.06em;
    margin-right: 2px;
}

/* Card inner layout — flex row */
.match-card-inner {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}
.match-team {
    flex: 1;
    min-width: 100px;
    text-align: center;
}
.match-team-name {
    font-family: 'Chakra Petch', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-primary);
    margin-top: 4px;
}
.match-team img {
    max-height: 44px;
    object-fit: contain;
}
.match-score-area {
    flex: 0 0 auto;
    text-align: center;
    min-width: 70px;
}
.match-score {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    color: var(--text-primary);
    letter-spacing: 0.06em;
    line-height: 1;
}
.match-score.pending {
    font-size: 1rem;
    color: var(--text-muted);
    font-family: 'Chakra Petch', sans-serif;
}
.match-status-badge {
    display: inline-block;
    font-family: 'Chakra Petch', sans-serif;
    font-weight: 600;
    font-size: 0.7rem;
    padding: 3px 10px;
    border-radius: 12px;
    color: #fff;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.match-meta {
    margin-top: 8px;
    font-family: 'Chakra Petch', sans-serif;
    font-size: 0.72rem;
    color: var(--text-muted);
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}

/* ── Responsive: mobile ── */
@media (max-width: 640px) {
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.15rem !important; }

    .match-card { padding: 0.75rem 0.85rem; }
    .match-card-inner { gap: 0.4rem; }
    .match-team { min-width: 70px; }
    .match-team-name { font-size: 0.78rem; }
    .match-team img { max-height: 30px; }
    .match-score { font-size: 1.3rem; }
    .match-score-area { min-width: 48px; }
    .match-date-badge { font-size: 0.7rem; padding: 3px 10px; }
    .match-date-big { font-size: 1rem; }
    .match-meta { font-size: 0.65rem; gap: 6px; }

    [data-testid="stMetric"] { padding: 0.75rem 0.5rem; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
}

/* ── Responsive: tablet ── */
@media (min-width: 641px) and (max-width: 1024px) {
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.6rem !important; }
}
"""

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

STATUS_MAP = {
    "SCHEDULED": ("Upcoming", "#5a6a7a"),
    "TIMED": ("Upcoming", "#5a6a7a"),
    "LIVE": ("● LIVE", "#e67e22"),
    "IN_PLAY": ("● LIVE", "#e67e22"),
    "PAUSED": ("Half Time", "#e67e22"),
    "FINISHED": ("Full Time", "#27ae60"),
    "AWARDED": ("Awarded", "#27ae60"),
    "POSTPONED": ("Postponed", "#e74c3c"),
    "CANCELLED": ("Cancelled", "#e74c3c"),
    "SUSPENDED": ("Suspended", "#e74c3c"),
}


def match_card(match, expanded: bool = False):
    """Render a single match as a responsive HTML card with highlighted date."""
    home_name = match["homeTeam"].get("name", "TBD") or "TBD"
    away_name = match["awayTeam"].get("name", "TBD") or "TBD"
    home_crest = match["homeTeam"].get("crest") or ""
    away_crest = match["awayTeam"].get("crest") or ""

    score = match.get("score") or {}
    full_time = score.get("fullTime") or {}
    home_goals = full_time.get("home") if full_time.get("home") is not None else None
    away_goals = full_time.get("away") if full_time.get("away") is not None else None

    status = match.get("status") or "SCHEDULED"
    status_label, badge_color = STATUS_MAP.get(status, (status, "#5a6a7a"))

    utc_date = match.get("utcDate") or ""
    match_date = utc_date[:10]
    match_time = utc_date[11:16] if utc_date else ""

    match_time_utc7 = ""
    if utc_date:
        try:
            utc_dt = datetime.strptime(
                utc_date.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z"
            )
            utc7_tz = timezone(timedelta(hours=7))
            utc7_dt = utc_dt.astimezone(utc7_tz)
            match_time_utc7 = utc7_dt.strftime("%H:%M")
        except (ValueError, AttributeError):
            pass

    stage = (match.get("stage") or "").replace("_", " ").title()
    group = (match.get("group") or "").replace("_", " ").replace("GROUP ", "Group ")

    is_live = status in ("LIVE", "IN_PLAY", "PAUSED")
    has_score = status in ("FINISHED", "AWARDED", "LIVE", "IN_PLAY", "PAUSED")

    live_class = " live" if is_live else ""

    # Format date nicely
    try:
        dt = datetime.strptime(match_date, "%Y-%m-%d")
        date_display = dt.strftime("%a %d %b %Y")
    except ValueError:
        date_display = match_date

    # Score display
    if has_score and home_goals is not None:
        score_html = f'<div class="match-score">{home_goals} – {away_goals}</div>'
    else:
        score_html = '<div class="match-score pending">vs</div>'

    # Crest images
    home_img = f'<img src="{home_crest}" alt="" style="max-height:44px">' if home_crest else ""
    away_img = f'<img src="{away_crest}" alt="" style="max-height:44px">' if away_crest else ""

    # Meta line
    meta_parts = []
    if expanded:
        if stage:
            meta_parts.append(f"📍 {stage}")
        if group and "Group" in group:
            meta_parts.append(group)
        if match_time and match_time_utc7:
            meta_parts.append(f"⏰ {match_time} UTC / {match_time_utc7} VN Time")
        elif match_time:
            meta_parts.append(f"⏰ {match_time} UTC")
    meta_html = "".join(f"<span>{p}</span>" for p in meta_parts)

    html = f"""
    <div class="match-card{live_class}">
        <div class="match-date-badge">
            📅 <span class="match-date-big">{date_display}</span>
            {f'<span>· {match_time} UTC / {match_time_utc7} Viet Nam</span>' if match_time and match_time_utc7 else f'<span>· {match_time} UTC</span>' if match_time else ''}
        </div>
        <div class="match-card-inner">
            <div class="match-team">
                {home_img}
                <div class="match-team-name">{home_name}</div>
            </div>
            <div class="match-score-area">
                {score_html}
            </div>
            <div class="match-team">
                {away_img}
                <div class="match-team-name">{away_name}</div>
            </div>
            <div style="flex:0 0 auto;text-align:center">
                <span class="match-status-badge" style="background:{badge_color}">{status_label}</span>
            </div>
        </div>
        {f'<div class="match-meta">{meta_html}</div>' if meta_html else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def group_standings_table(groups: dict):
    """Render group stage standings with responsive layout."""
    if not groups:
        st.info("No group standings available yet.")
        return

    tabs = st.tabs(list(groups.keys()))
    for tab, (group_name, table) in zip(tabs, groups.items()):
        with tab:
            if not table:
                st.info(f"No standings for {group_name} yet.")
                continue

            # Responsive column widths: rank, team, P, W, D, L, GF, GA, Pts
            cols = st.columns([0.4, 2.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.6])
            headers = ["#", "Team", "P", "W", "D", "L", "GF", "GA", "Pts"]
            for col, h in zip(cols, headers):
                col.markdown(
                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:0.85rem;"
                    f"color:var(--gold-bright);letter-spacing:0.05em'>{h}</span>",
                    unsafe_allow_html=True,
                )

            for row in table:
                rank = row["position"]
                team_obj = row.get("team") or {}
                team_name = team_obj.get("name", "?")
                crest = team_obj.get("crest") or ""
                played = row["playedGames"]
                won = row["won"]
                drawn = row["draw"]
                lost = row["lost"]
                gf = row["goalsFor"]
                ga = row["goalsAgainst"]
                pts = row["points"]

                rcols = st.columns([0.4, 2.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.6])
                rcols[0].write(str(rank))
                with rcols[1]:
                    if crest:
                        st.image(crest, width=20)
                    st.markdown(
                        f"<span style='font-family:Chakra Petch,sans-serif;font-size:0.82rem'>"
                        f"{team_name}</span>",
                        unsafe_allow_html=True,
                    )
                rcols[2].write(str(played))
                rcols[3].write(str(won))
                rcols[4].write(str(drawn))
                rcols[5].write(str(lost))
                rcols[6].write(str(gf))
                rcols[7].write(str(ga))
                rcols[8].markdown(
                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:1rem;"
                    f"color:var(--gold-bright)'>{pts}</span>",
                    unsafe_allow_html=True,
                )


def teams_grid(teams_data: dict):
    """Display teams in a responsive grid."""
    teams = teams_data.get("teams", [])
    if not teams:
        st.info("No team data available yet.")
        return

    cols = st.columns(4)
    for i, team in enumerate(sorted(teams, key=lambda t: t.get("name", ""))):
        with cols[i % 4]:
            crest = team.get("crest", "")
            if crest:
                st.image(crest, width=64)
            st.markdown(
                f"<span style='font-family:Chakra Petch,sans-serif;font-weight:600;"
                f"font-size:0.9rem'>{team.get('name', '?')}</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"{team.get('venue', 'TBD')}  •  {team.get('tla', '')}")
            coach = team.get("coach") or {}
            if coach.get("name"):
                st.caption(f"Coach: {team['coach']['name']}")
```

---

### Task 5: Create `world_cup/app.py` — orchestration layer

**Files:**
- Create: `world_cup/app.py`

**Rationale:** This is the new entry point. It imports from `api` and `components`, adds `@st.cache_data` wrappers, and contains all the Streamlit UI scaffolding (sidebar, routing, pagination, error handling) extracted from the original file lines 550-765.

- [ ] **Step 1: Write `world_cup/app.py`**

```python
import streamlit as st
import requests
from datetime import datetime

from world_cup import api
from world_cup.components import (
    GLOBAL_CSS,
    match_card,
    group_standings_table,
    teams_grid,
)


# ---------------------------------------------------------------------------
# Cached data wrappers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="World Cup 2026 Dashboard",
    page_icon="🏆",
    layout="wide",
)

# Inject global CSS
st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)

st.title("🏆 World Cup 2026")
st.markdown(
    "<p style='color:var(--text-muted);font-family:Chakra Petch,sans-serif;margin-top:-0.5rem'>"
    "Host: USA · Canada · Mexico &nbsp;|&nbsp; "
    f"Data via football-data.org &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    "</p>",
    unsafe_allow_html=True,
)

# Sidebar
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
    "",
    ["📊 Overview", "📅 Matches", "📋 Group Standings", "🌍 Teams"],
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

except requests.exceptions.RequestException as e:
    st.error(f"API connection error: {e}")
except Exception as e:
    st.error(f"Error: {e}")
```

---

### Task 6: Replace `world_cup_dashboard.py` with launcher

**Files:**
- Replace: `world_cup_dashboard.py`

**Rationale:** The original 766-line file is now the four files in `world_cup/`. Replace it with a thin launcher so the user can still run `streamlit run world_cup_dashboard.py`.

- [ ] **Step 1: Overwrite `world_cup_dashboard.py`**

```python
"""World Cup 2026 Dashboard — launcher."""
from world_cup import app
```

(All logic runs on import via `world_cup/app.py`.)

---

### Task 7: Verify

- [ ] **Step 1: Verify `api.py` has no Streamlit dependency**

Run: `python -c "from world_cup.api import fetch_standings; print('api.py imports OK')"`
Expected: `api.py imports OK`

- [ ] **Step 2: Verify the full app imports**

Run: `python -c "from world_cup import app; print('app imports OK')"`
Expected: `app imports OK` (Streamlit will initialize but not start the server)

- [ ] **Step 3: Launch the dashboard**

Run: `streamlit run world_cup_dashboard.py`

Expected: Dashboard loads with all four views working identically to before the split.
