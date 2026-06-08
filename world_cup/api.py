import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")

try:
    import streamlit as st  # noqa: F811
    API_KEY = st.secrets.get("API_FOOTBALL_KEY", API_KEY)
except Exception:
    pass
BASE_URL = "https://api.football-data.org/v4"


def _headers():
    return {"X-Auth-Token": API_KEY}
COMPETITION_CODE = "WC"
SEASON = 2026

_MIN_INTERVAL = 3.0
_MAX_RETRIES = 3
_last_call = 0.0


def api_get(endpoint: str, params: dict | None = None) -> dict:
    if params is None:
        params = {}
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(_MAX_RETRIES):
        _throttle()
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)

        if resp.status_code == 403 and attempt < _MAX_RETRIES - 1:
            delay = 2 ** attempt * 2
            time.sleep(delay)
            continue

        resp.raise_for_status()
        return resp.json()


def _throttle():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.time()


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
