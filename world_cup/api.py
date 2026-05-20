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
