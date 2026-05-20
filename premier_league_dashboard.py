"""
Premier League Dashboard — fetches fixtures, scores, results, and standings
from API-Football (dashboard.api-football.com) and displays them via Streamlit.
"""

import os
import streamlit as st
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

PREMIER_LEAGUE_ID = 39
SEASON = 2024  # 2024/25 season


def api_get(endpoint: str, params: dict) -> dict:
    """Call the API-Football v3 endpoint and return JSON."""
    if not API_KEY:
        st.error("Missing API_FOOTBALL_KEY environment variable. Set it in a .env file.")
        st.stop()
    url = f"{BASE_URL}{endpoint}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        st.error(f"API error: {data['errors']}")
        st.stop()
    return data


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def fetch_standings():
    return api_get("/standings", {"league": PREMIER_LEAGUE_ID, "season": SEASON})


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fixtures_by_status(status: str):
    return api_get("/fixtures", {
        "league": PREMIER_LEAGUE_ID,
        "season": SEASON,
        "status": status,
    })


@st.cache_data(ttl=60, show_spinner=False)
def fetch_live_fixtures():
    return api_get("/fixtures", {"live": str(PREMIER_LEAGUE_ID)})


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def fixture_card(match, expanded: bool = False):
    """Render a single match as a readable card."""
    fixture = match["fixture"]
    league = match["league"]
    teams = match["teams"]
    goals = match["goals"]

    home = teams["home"]["name"]
    away = teams["away"]["name"]
    home_logo = teams["home"]["logo"]
    away_logo = teams["away"]["logo"]
    home_goals = goals["home"] if goals["home"] is not None else "-"
    away_goals = goals["away"] if goals["away"] is not None else "-"
    status = fixture["status"]["short"]
    elapsed = fixture["status"].get("elapsed")

    status_map = {
        "FT": "Full Time", "AET": "AET", "PEN": "Pens",
        "1H": "1st Half", "HT": "Half Time", "2H": "2nd Half",
        "NS": "Not Started", "TBD": "TBD", "PST": "Postponed",
        "CANC": "Cancelled", "ABD": "Abandoned",
    }
    status_label = status_map.get(status, status)

    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 1])

    with col1:
        st.markdown(
            f"<div style='text-align:right;font-size:1.1rem;font-weight:600'>{home}</div>",
            unsafe_allow_html=True,
        )
        if home_logo:
            st.image(home_logo, width=40)

    with col2:
        if status in ("FT", "AET", "PEN", "1H", "HT", "2H"):
            st.markdown(
                f"<div style='text-align:center;font-size:1.5rem;font-weight:700'>{home_goals} - {away_goals}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='text-align:center;font-size:1.2rem;color:#888'>vs</div>",
                unsafe_allow_html=True,
            )

    with col4:
        st.markdown(
            f"<div style='font-size:1.1rem;font-weight:600'>{away}</div>",
            unsafe_allow_html=True,
        )
        if away_logo:
            st.image(away_logo, width=40)

    with col5:
        badge_color = "#27ae60" if status in ("FT", "AET", "PEN") else "#e67e22" if status in ("1H", "HT", "2H") else "#95a5a6"
        elapsed_display = f" {elapsed}'" if elapsed else ""
        st.markdown(
            f"<span style='background:{badge_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem'>{status_label}{elapsed_display}</span>",
            unsafe_allow_html=True,
        )

    with col3:
        if not expanded:
            st.caption(fixture["date"][:10])

    if expanded:
        st.caption(f"📍 {fixture['venue']['name'] if fixture['venue']['name'] else 'TBD'}  •  {fixture['date'][:10]}")
        st.caption(f"Round: {league.get('round', 'N/A')}  •  Referee: {fixture['referee'] or 'TBD'}")

    st.markdown("---")


def standings_table(data):
    """Render league standings table."""
    if not data.get("response") or not data["response"][0].get("league", {}).get("standings"):
        st.info("No standings data available for this season yet.")
        return

    standings_rows = data["response"][0]["league"]["standings"][0]

    rows = []
    for row in standings_rows:
        rank = row["rank"]
        team_name = row["team"]["name"]
        logo = row["team"]["logo"]
        played = row["all"]["played"]
        wins = row["all"]["win"]
        draws = row["all"]["draw"]
        losses = row["all"]["lose"]
        gf = row["all"]["goals"]["for"]
        ga = row["all"]["goals"]["against"]
        gd = row["goalsDiff"]
        pts = row["points"]
        form = row.get("form", "")

        form_html = ""
        for ch in form[-5:]:
            color = "#27ae60" if ch == "W" else "#e74c3c" if ch == "L" else "#95a5a6"
            form_html += f"<span style='background:{color};color:white;padding:1px 5px;margin:1px;border-radius:3px;font-size:0.7rem'>{ch}</span>"

        rows.append({
            "rank": rank, "team": team_name, "logo": logo,
            "P": played, "W": wins, "D": draws, "L": losses,
            "GF": gf, "GA": ga, "GD": gd, "Pts": pts,
            "form": form_html,
        })

    top4 = {"rank": 4, "color": "#4285f4", "label": "UCL"}
    top5 = {"rank": 5, "color": "#f4b400", "label": "EL"}
    relegation = {"rank": 18, "color": "#e74c3c", "label": "REL"}

    mark = f"<div style='display:flex;gap:12px;margin-bottom:8px;font-size:0.8rem'>"
    for zone in [top4, top5, relegation]:
        mark += f"<span style='border-left:3px solid {zone['color']};padding-left:4px'>{zone['label']}</span>"
    mark += "</div>"
    st.markdown(mark, unsafe_allow_html=True)

    cols = st.columns([0.5, 0.5, 2.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.8, 1.5])
    headers = ["#", "", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "Form"]
    for col, h in zip(cols, headers):
        col.markdown(f"**{h}**")

    for row_data in rows:
        zone_color = None
        if row_data["rank"] <= top4["rank"]:
            zone_color = top4["color"]
        elif row_data["rank"] <= top5["rank"]:
            zone_color = top5["color"]
        elif row_data["rank"] >= relegation["rank"]:
            zone_color = relegation["color"]

        style = f"border-left: 3px solid {zone_color}; padding-left: 4px;" if zone_color else ""

        cols = st.columns([0.5, 0.5, 2.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.8, 1.5])
        cols[0].markdown(f"<div style='{style}'>{row_data['rank']}</div>", unsafe_allow_html=True)
        if row_data["logo"]:
            cols[1].image(row_data["logo"], width=20)
        else:
            cols[1].write("")
        cols[2].write(row_data["team"])
        cols[3].write(str(row_data["P"]))
        cols[4].write(str(row_data["W"]))
        cols[5].write(str(row_data["D"]))
        cols[6].write(str(row_data["L"]))
        cols[7].write(str(row_data["GF"]))
        cols[8].write(str(row_data["GA"]))
        cols[9].write(str(row_data["GD"]))
        cols[10].markdown(f"**{row_data['Pts']}**")
        cols[11].markdown(row_data["form"], unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Premier League Dashboard",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ Premier League Dashboard")
st.caption(f"Season 2024/25 — data via API-Football • {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ------- Sidebar -------
st.sidebar.markdown("## 🔑 API Key")
st.sidebar.text_input(
    "API-Football Key",
    value=API_KEY if API_KEY else "",
    type="password",
    key="api_key_input",
    help="Get your key at https://dashboard.api-football.com/",
)
st.sidebar.markdown("---")
view = st.sidebar.radio(
    "View",
    ["📊 Overview", "📅 Fixtures & Results", "📋 Standings", "🔥 Live"],
)

# Override key if entered in sidebar
if st.session_state.get("api_key_input") and not API_KEY:
    API_KEY = st.session_state.api_key_input
    HEADERS["x-apisports-key"] = API_KEY

if not API_KEY:
    st.warning("Enter your API-Football key in the sidebar to get started.")
    st.stop()

# ------- Tabs -------

if view == "📊 Overview":
    st.subheader("League Table (Top 6)")
    with st.spinner("Loading standings..."):
        standings = fetch_standings()
        if standings.get("response") and standings["response"][0].get("league", {}).get("standings"):
            top6 = standings["response"][0]["league"]["standings"][0][:6]
            cols = st.columns(6)
            for i, row in enumerate(top6):
                with cols[i]:
                    logo = row["team"]["logo"]
                    if logo:
                        st.image(logo, width=48)
                    st.markdown(f"**{i+1}. {row['team']['name']}**")
                    st.metric("Points", row["points"], f"GD {row['goalsDiff']}")
                    st.caption(f"P{row['all']['played']} W{row['all']['win']} D{row['all']['draw']} L{row['all']['lose']}")
        else:
            st.info("No standings yet.")

    st.markdown("---")
    st.subheader("🔥 Live / Recent Results")
    with st.spinner("Loading recent matches..."):
        recent = fetch_fixtures_by_status("FT-AET-PEN")
        fixtures_list = (recent.get("response") or [])[-6:]
        if fixtures_list:
            for m in reversed(fixtures_list):
                fixture_card(m, expanded=False)
        else:
            st.info("No recent results.")

    st.markdown("---")
    st.subheader("📅 Upcoming Fixtures")
    with st.spinner("Loading upcoming fixtures..."):
        upcoming = fetch_fixtures_by_status("NS-TBD")
        upcoming_list = (upcoming.get("response") or [])[:6]
        if upcoming_list:
            for m in upcoming_list:
                fixture_card(m, expanded=False)
        else:
            st.info("No upcoming fixtures.")


elif view == "📅 Fixtures & Results":
    tab1, tab2, tab3 = st.tabs(["🔴 Live", "✅ Results", "📅 Upcoming"])

    with tab1:
        st.subheader("Live Matches")
        with st.spinner("Checking live matches..."):
            live = fetch_live_fixtures()
            live_list = live.get("response") or []
            if live_list:
                for m in live_list:
                    fixture_card(m, expanded=True)
            else:
                st.info("No live Premier League matches right now.")

    with tab2:
        st.subheader("Completed Results")
        with st.spinner("Loading results..."):
            results = fetch_fixtures_by_status("FT-AET-PEN")
            results_list = (results.get("response") or [])[-20:]
            if results_list:
                for m in reversed(results_list):
                    fixture_card(m, expanded=True)
            else:
                st.info("No results yet this season.")

    with tab3:
        st.subheader("Upcoming Fixtures")
        with st.spinner("Loading fixtures..."):
            upcoming = fetch_fixtures_by_status("NS-TBD-PST")
            upcoming_list = (upcoming.get("response") or [])[:20]
            if upcoming_list:
                for m in upcoming_list:
                    fixture_card(m, expanded=True)
            else:
                st.info("No upcoming fixtures.")


elif view == "📋 Standings":
    st.subheader("Premier League 2024/25 — Full Table")
    with st.spinner("Loading standings..."):
        data = fetch_standings()
        standings_table(data)


elif view == "🔥 Live":
    st.subheader("Live Now")
    with st.spinner("Loading live data..."):
        live = fetch_live_fixtures()
        live_list = live.get("response") or []
        if live_list:
            for m in live_list:
                fixture_card(m, expanded=True)
                home = m["teams"]["home"]
                away = m["teams"]["away"]
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(home["name"], f"{m['goals']['home'] or 0}")
                with col2:
                    st.metric(away["name"], f"{m['goals']['away'] or 0}")
        else:
            st.info("No live Premier League matches right now. Check back on matchdays!")

    st.markdown("---")
    st.subheader("Recent Results")
    with st.spinner("Loading recent results..."):
        recent = fetch_fixtures_by_status("FT-AET-PEN")
        recent_list = (recent.get("response") or [])[-5:]
        if recent_list:
            for m in reversed(recent_list):
                fixture_card(m, expanded=False)
