# World Cup Dashboard — Front-End / Back-End Split

Date: 2026-05-19
Status: approved

## Goal

Split `world_cup_dashboard.py` (766-line monolithic Streamlit app) into a three-module package
with a clean separation between data fetching, UI rendering, and orchestration.

## Scope

- Only `world_cup_dashboard.py` — `premier_league_dashboard.py` is out of scope.
- No behavior changes, no UI changes. Pure structural split.
- Move hardcoded API key to `.env`.

## Target structure

```
world_cup/
├── __init__.py      # empty
├── api.py           # data layer — zero Streamlit dependency
├── components.py    # UI renderers — Streamlit-dependent, data-agnostic
└── app.py           # orchestration — caching, routing, sidebar, pagination

world_cup_dashboard.py  # replaced by: streamlit run world_cup/app.py
```

## Module contracts

### `api.py` — Data layer

Imports: `os`, `requests`, `datetime`, `dotenv`. No Streamlit.

| Item | Role |
|------|------|
| `api_get(endpoint, params)` | Thin HTTP wrapper around football-data.org v4. Raises on error. |
| `fetch_matches()` | `GET /competitions/WC/matches?season=2026` |
| `fetch_standings()` | `GET /competitions/WC/standings?season=2026` |
| `fetch_teams()` | `GET /competitions/WC/teams?season=2026` |
| `fetch_group_standings()` | Calls `fetch_standings()`, returns `{group_name: [table_rows]}` |

Constants: `API_KEY` (from env), `BASE_URL`, `HEADERS`, `COMPETITION_CODE`, `SEASON`.

No `@st.cache_data` — caching is `app.py`'s job.

### `components.py` — UI layer

Imports: `streamlit as st`, `datetime` (stdlib). Reads constants from `api.py` for `STATUS_MAP`.

| Item | Signature | Notes |
|------|-----------|-------|
| `GLOBAL_CSS` | string constant | Unchanged, 290 lines of CSS |
| `STATUS_MAP` | dict constant | Unchanged |
| `match_card(match, expanded)` | renders HTML | Calls `st.markdown` with `unsafe_allow_html=True` |
| `group_standings_table(groups)` | renders tabs+tables | Calls `st.tabs`, `st.columns`, `st.image` |
| `teams_grid(teams_data)` | renders 4-col grid | Calls `st.columns`, `st.image` |

Rule: functions receive data as arguments. They never call the API directly.

### `app.py` — Orchestration layer

Imports: `streamlit as st`, `api`, `components`.

Responsibilities:
- Thin `@st.cache_data` wrappers around `api.fetch_*()` functions
- `st.set_page_config` + CSS injection
- Sidebar navigation (4 views: Overview, Matches, Group Standings, Teams)
- All pagination logic (session state keys carry over unchanged)
- Top-level `try/except` for API errors

No function internals change. The original `world_cup_dashboard.py` is replaced by
running `streamlit run world_cup/app.py`.

## Non-functional

- **API key**: moved to `API_FOOTBALL_KEY` in `.env` (same pattern as `premier_league_dashboard.py`)
- **Dependencies**: no new packages — `python-dotenv` already in `requirements.txt`
- **Cache TTLs**: unchanged (300s matches, 600s standings/teams, 300s group standings)
- **Target users**: ~100, infrequent — single-service deployment (`streamlit run`)

## Verification

1. `python -c "from world_cup.api import fetch_matches; print(fetch_matches())"` — plain Python, no Streamlit
2. `streamlit run world_cup/app.py` — all four views render identically to current behavior
3. API key loads from `.env`, not hardcoded

## Out of scope

- Refactoring function internals (e.g., deduplicating pagination)
- Changing CSS or visual design
- Changing the API provider or endpoint
- `premier_league_dashboard.py`
- Tests (no test framework currently in the project)
