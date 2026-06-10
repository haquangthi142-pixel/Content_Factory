import html
import streamlit as st
from datetime import datetime, timedelta, timezone

GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Chakra+Petch:wght@300;400;500;600;700&display=swap');

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

.stApp { background: var(--bg-deep); }
.stMainBlockContainer, .block-container { background: var(--bg-deep) !important; }

/* Hide default Streamlit header — Deploy button & hamburger menu */
header[data-testid="stHeader"] { display: none !important; }

section[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid var(--border-gold);
}
section[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
    font-family: 'Chakra Petch', sans-serif;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 1rem; padding: 0.5rem 0.75rem; border-radius: 8px; transition: all 0.2s;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: rgba(212,168,67,0.1); }

h1, h2, h3, h4 {
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: 0.04em; color: var(--text-primary) !important;
}
h1 { font-size: 2.8rem !important; }
h2 { font-size: 2rem !important; }
h3 { font-size: 1.5rem !important; }

p, span, div, caption, label, .stMarkdown, .stText {
    font-family: 'Chakra Petch', sans-serif; color: var(--text-primary);
}

[data-testid="stMetric"] {
    background: var(--bg-card); border: 1px solid var(--border-gold);
    border-radius: 12px; padding: 1.25rem 1rem; text-align: center;
}
[data-testid="stMetric"] label {
    font-family: 'Bebas Neue', sans-serif !important; font-size: 1rem !important;
    letter-spacing: 0.06em; color: var(--gold) !important; text-transform: uppercase;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', sans-serif !important; font-size: 2.6rem !important;
    color: var(--text-primary) !important;
}

.stButton button {
    font-family: 'Chakra Petch', sans-serif !important; font-weight: 600;
    border-radius: 8px; border: 1px solid var(--border-gold) !important;
    background: var(--bg-card) !important; color: var(--gold-bright) !important;
    transition: all 0.2s;
}
.stButton button:hover {
    background: var(--bg-card-hover) !important; border-color: var(--gold-bright) !important;
}
.stButton button:disabled {
    opacity: 0.35; border-color: var(--border-subtle) !important; color: var(--text-muted) !important;
}

.stTabs [data-baseweb="tab-list"] { gap: 0; background: var(--bg-card); border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Chakra Petch', sans-serif !important; font-weight: 600;
    color: var(--text-muted) !important; border-radius: 8px; padding: 0.5rem 1.2rem;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--gold) !important; color: #0a0e14 !important;
}

hr { border-color: var(--border-subtle) !important; margin: 0.5rem 0 !important; }

[data-testid="stInfo"], [data-testid="stNotification"] {
    background: var(--bg-card) !important; border: 1px solid var(--border-gold) !important;
    border-radius: 10px; color: var(--text-primary) !important;
}

.match-card {
    background: var(--bg-card); border: 1px solid var(--border-subtle);
    border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 0.75rem;
    transition: all 0.25s; position: relative; overflow: hidden;
}
.match-card::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0;
    width: 3px; background: var(--gold-dim); border-radius: 0 3px 3px 0;
}
.match-card:hover { border-color: var(--border-gold); background: var(--bg-card-hover); }
.match-card.live { border-color: rgba(230,126,34,0.5); animation: livePulse 2s infinite; }
.match-card.live::before { background: var(--accent-live); }
@keyframes livePulse {
    0%, 100% { box-shadow: 0 0 8px rgba(230,126,34,0.15); }
    50%      { box-shadow: 0 0 20px rgba(230,126,34,0.35); }
}

.match-date-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: linear-gradient(135deg, #1a3a1a 0%, #0d2b0d 100%);
    border: 1px solid var(--gold-dim); border-radius: 20px; padding: 4px 14px;
    margin-bottom: 10px; font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.8rem; color: var(--gold-bright); letter-spacing: 0.04em;
}
.match-date-big {
    font-family: 'Bebas Neue', sans-serif; font-size: 1.35rem;
    color: var(--gold-bright); letter-spacing: 0.06em; margin-right: 2px;
}

.match-card-inner { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.match-team { flex: 1; min-width: 100px; text-align: center; }
.match-team-name {
    font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.95rem; color: var(--text-primary); margin-top: 4px;
}
.match-team img { max-height: 44px; object-fit: contain; }
.match-score-area { flex: 0 0 auto; text-align: center; min-width: 70px; }
.match-score {
    font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem;
    color: var(--text-primary); letter-spacing: 0.06em; line-height: 1;
}
.match-score.pending { font-size: 1rem; color: var(--text-muted); font-family: 'Chakra Petch', sans-serif; }
.match-status-badge {
    display: inline-block; font-family: 'Chakra Petch', sans-serif; font-weight: 600;
    font-size: 0.7rem; padding: 3px 10px; border-radius: 12px; color: #fff;
    letter-spacing: 0.05em; text-transform: uppercase;
}
.match-meta {
    margin-top: 8px; font-family: 'Chakra Petch', sans-serif;
    font-size: 0.72rem; color: var(--text-muted); display: flex; gap: 12px; flex-wrap: wrap;
}

.match-handicap-badge {
    display: inline-block;
    margin-top: 0.5rem;
    font-family: 'Chakra Petch', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--gold-bright);
    background: rgba(212, 168, 67, 0.12);
    border: 1px solid rgba(212, 168, 67, 0.25);
    border-radius: 8px;
    padding: 3px 12px;
    letter-spacing: 0.03em;
}

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

@media (min-width: 641px) and (max-width: 1024px) {
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.6rem !important; }
}

/* ── Admin Buy Coins select ── */
[aria-label="Search player by phone"] {
    background: #000000 !important;
    color: #ffffff !important;
    border-color: rgba(255,255,255,0.25) !important;
}
[aria-label="Search player by phone"] * {
    color: #ffffff !important;
}

/* ── Sidebar number input: dark text ── */
section[data-testid="stSidebar"] input[type="number"],
section[data-testid="stSidebar"] .stNumberInput input {
    color: #000000 !important;
    background: #ffffff !important;
}
"""

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

    try:
        dt = datetime.strptime(match_date, "%Y-%m-%d")
        date_display = dt.strftime("%a %d %b %Y")
    except ValueError:
        date_display = match_date

    if has_score and home_goals is not None:
        score_html = f'<div class="match-score">{home_goals} – {away_goals}</div>'
    else:
        score_html = '<div class="match-score pending">vs</div>'

    home_img = f'<img src="{home_crest}" alt="" style="max-height:44px">' if home_crest else ""
    away_img = f'<img src="{away_crest}" alt="" style="max-height:44px">' if away_crest else ""

    meta_parts = []
    if expanded:
        if stage:
            meta_parts.append(f"\U0001f4cd {stage}")
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
            \U0001f4c5 <span class="match-date-big">{date_display}</span>
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


def match_card_db(match: dict):
    """Render a DB match row using the match-card CSS (same style as Overview tab)."""
    home_name = match["team_a"] or "TBD"
    away_name = match["team_b"] or "TBD"
    home_crest = match.get("crest_a") or ""
    away_crest = match.get("crest_b") or ""
    status = match.get("status") or "Not Started"
    score_a = match.get("score_a")
    score_b = match.get("score_b")

    # Status label & color
    if status == "Live":
        status_label, badge_color = "● LIVE", "#e67e22"
    elif status == "Finished":
        status_label, badge_color = "Full Time", "#27ae60"
    else:
        status_label, badge_color = "Upcoming", "#5a6a7a"

    is_live = status == "Live"

    # Time parsing
    utc_str = match.get("match_time") or ""
    match_date = utc_str[:10] if utc_str else ""
    match_time_utc = utc_str[11:16] if len(utc_str) >= 16 else ""
    match_time_vn = ""
    if utc_str:
        try:
            from datetime import timezone as _tz, timedelta as _td
            utc_dt = datetime.strptime(utc_str.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
            vn_tz = _tz(_td(hours=7))
            vn_dt = utc_dt.astimezone(vn_tz)
            match_time_vn = vn_dt.strftime("%H:%M")
        except (ValueError, AttributeError):
            pass

    try:
        dt = datetime.strptime(match_date, "%Y-%m-%d")
        date_display = dt.strftime("%a %d %b %Y")
    except ValueError:
        date_display = match_date

    # Score
    if status == "Finished" and score_a is not None and score_b is not None:
        score_html = f'<div class="match-score">{score_a} – {score_b}</div>'
    elif is_live and score_a is not None and score_b is not None:
        score_html = f'<div class="match-score">{score_a} – {score_b}</div>'
    else:
        score_html = '<div class="match-score pending">vs</div>'

    home_img = f'<img src="{home_crest}" alt="" style="max-height:44px">' if home_crest else ""
    away_img = f'<img src="{away_crest}" alt="" style="max-height:44px">' if away_crest else ""

    live_class = " live" if is_live else ""

    # Handicap badge — show favorite gives N goals
    h_line = match.get("handicap_line")
    h_fav = match.get("handicap_favorite")
    handicap_html = ""
    if h_line is not None and h_fav is not None:
        fav_name = home_name if h_fav == "A" else away_name
        und_name = away_name if h_fav == "A" else home_name
        handicap_html = f"""
        <div class="match-handicap-badge" title="Handicap: {html.escape(fav_name)} −{h_line} vs {html.escape(und_name)} +{h_line}">
            ⚽ {html.escape(fav_name)} −{h_line} &nbsp;·&nbsp; {html.escape(und_name)} +{h_line}
        </div>"""

    st.markdown(f"""
    <div class="match-card{live_class}">
        <div class="match-date-badge">
            \U0001f4c5 <span class="match-date-big">{date_display}</span>
            {f'<span>· {match_time_utc} UTC / {match_time_vn} VN</span>' if match_time_utc and match_time_vn else f'<span>· {match_time_utc} UTC</span>' if match_time_utc else ''}
        </div>
        <div class="match-card-inner">
            <div class="match-team">
                {home_img}
                <div class="match-team-name">{html.escape(home_name)}</div>
            </div>
            <div class="match-score-area">
                {score_html}
            </div>
            <div class="match-team">
                {away_img}
                <div class="match-team-name">{html.escape(away_name)}</div>
            </div>
            <div style="flex:0 0 auto;text-align:center">
                <span class="match-status-badge" style="background:{badge_color}">{status_label}</span>
            </div>
        </div>
        {handicap_html}
    </div>
    """, unsafe_allow_html=True)


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
