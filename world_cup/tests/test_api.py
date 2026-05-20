import pytest
import requests
from unittest.mock import patch, MagicMock

from world_cup import api


# ===========================================================================
# api_get
# ===========================================================================

def test_api_get_constructs_url_and_headers_correctly(mocker):
    mock_get = mocker.patch("requests.get")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    mock_get.return_value = mock_resp

    result = api.api_get("/test/endpoint", {"season": 2026})

    mock_get.assert_called_once()
    call_args, call_kwargs = mock_get.call_args
    assert call_args[0] == "https://api.football-data.org/v4/test/endpoint"
    assert "X-Auth-Token" in call_kwargs["headers"]
    assert call_kwargs["params"] == {"season": 2026}
    assert call_kwargs["timeout"] == 15
    assert result == {"ok": True}


def test_api_get_raises_on_http_error(mocker):
    mock_get = mocker.patch("requests.get")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
    mock_get.return_value = mock_resp

    with pytest.raises(requests.HTTPError, match="401"):
        api.api_get("/test")


def test_api_get_defaults_params_to_empty_dict(mocker):
    mock_get = mocker.patch("requests.get")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    mock_get.return_value = mock_resp

    api.api_get("/no-params")

    _, call_kwargs = mock_get.call_args
    assert call_kwargs["params"] == {}


# ===========================================================================
# fetch_matches
# ===========================================================================

def test_fetch_matches_calls_correct_endpoint(mocker):
    mock_api_get = mocker.patch.object(api, "api_get")
    mock_api_get.return_value = {"matches": []}

    result = api.fetch_matches()

    mock_api_get.assert_called_once_with(
        "/competitions/WC/matches", {"season": 2026}
    )
    assert result == {"matches": []}


# ===========================================================================
# fetch_standings
# ===========================================================================

def test_fetch_standings_calls_correct_endpoint(mocker):
    mock_api_get = mocker.patch.object(api, "api_get")
    mock_api_get.return_value = {"standings": []}

    result = api.fetch_standings()

    mock_api_get.assert_called_once_with(
        "/competitions/WC/standings", {"season": 2026}
    )
    assert result == {"standings": []}


# ===========================================================================
# fetch_teams
# ===========================================================================

def test_fetch_teams_calls_correct_endpoint(mocker):
    mock_api_get = mocker.patch.object(api, "api_get")
    mock_api_get.return_value = {"teams": [], "count": 0}

    result = api.fetch_teams()

    mock_api_get.assert_called_once_with(
        "/competitions/WC/teams", {"season": 2026}
    )
    assert result == {"teams": [], "count": 0}


# ===========================================================================
# fetch_group_standings
# ===========================================================================

def test_fetch_group_standings_groups_by_group_name(mocker):
    mock_api_get = mocker.patch.object(api, "api_get")
    mock_api_get.return_value = {
        "standings": [
            {
                "group": "GROUP_A",
                "table": [
                    {"position": 1, "team": {"name": "Team A1"}, "points": 9},
                    {"position": 2, "team": {"name": "Team A2"}, "points": 6},
                ],
            },
            {
                "group": "GROUP_B",
                "table": [
                    {"position": 1, "team": {"name": "Team B1"}, "points": 7},
                ],
            },
        ]
    }

    result = api.fetch_group_standings()

    assert "Group A" in result
    assert "Group B" in result
    assert len(result["Group A"]) == 2
    assert len(result["Group B"]) == 1
    assert result["Group A"][0]["team"]["name"] == "Team A1"


def test_fetch_group_standings_empty(mocker):
    mock_api_get = mocker.patch.object(api, "api_get")
    mock_api_get.return_value = {}

    result = api.fetch_group_standings()
    assert result == {}


def test_fetch_group_standings_handles_missing_group_field(mocker):
    mock_api_get = mocker.patch.object(api, "api_get")
    mock_api_get.return_value = {
        "standings": [
            {
                "table": [
                    {"position": 1, "team": {"name": "Team X"}, "points": 3},
                ],
            }
        ]
    }

    result = api.fetch_group_standings()
    assert "Unknown" in result
    assert len(result["Unknown"]) == 1
