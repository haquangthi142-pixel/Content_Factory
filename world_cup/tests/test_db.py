import sqlite3
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest

import world_cup.db as db_module


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    """Replace the database with a fresh temp-file copy for every test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(db_module, "DB_PATH", path)
    # Rebind get_connection so every call uses the same temp file
    monkeypatch.setattr(db_module, "get_connection", lambda: _test_conn(path))
    db_module.init_db()
    yield
    # Teardown
    os.unlink(path)


def _test_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================================
# Database initialisation
# ===========================================================================

def test_init_db_creates_tables():
    conn = db_module.get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    names = [r["name"] for r in tables]
    for t in ("users", "matches", "bets", "coin_transactions", "mission_logs"):
        assert t in names


# ===========================================================================
# Users
# ===========================================================================

def test_register_user_creates_user_with_starting_coins():
    uid = db_module.register_user("+84123456789", "Test User")
    assert uid == 1

    user = db_module.get_user(uid)
    assert user["phone"] == "+84123456789"
    assert user["full_name"] == "Test User"
    assert user["current_coins"] == 1000

    # Check initial coin transaction was recorded
    conn = db_module.get_connection()
    txs = conn.execute(
        "SELECT * FROM coin_transactions WHERE user_id = ?", (uid,)
    ).fetchall()
    conn.close()
    assert len(txs) == 1
    assert txs[0]["type"] == "initial"
    assert txs[0]["amount"] == 1000


def test_get_user_by_phone_finds_correct_user():
    db_module.register_user("+84111111111", "Alice")
    db_module.register_user("+84222222222", "Bob")

    alice = db_module.get_user_by_phone("+84111111111")
    assert alice["full_name"] == "Alice"

    bob = db_module.get_user_by_phone("+84222222222")
    assert bob["full_name"] == "Bob"


def test_get_user_by_phone_returns_none_for_unknown():
    assert db_module.get_user_by_phone("+84999999999") is None


def test_get_user_returns_none_for_bad_id():
    assert db_module.get_user(999) is None


def test_get_user_coins():
    uid = db_module.register_user("+84333333333", "Charlie")
    assert db_module.get_user_coins(uid) == 1000


# ===========================================================================
# Coin helpers
# ===========================================================================

def test_deduct_coins():
    uid = db_module.register_user("+84444444444", "Dana")
    db_module.deduct_coins(uid, 200, "bet", "Bet on match #1")

    assert db_module.get_user_coins(uid) == 800

    conn = db_module.get_connection()
    txs = conn.execute(
        "SELECT * FROM coin_transactions WHERE user_id = ? AND type = 'bet'", (uid,)
    ).fetchall()
    conn.close()
    assert len(txs) == 1
    assert txs[0]["amount"] == -200


def test_add_coins():
    uid = db_module.register_user("+84555555555", "Eve")
    db_module.add_coins(uid, 500, "mission", "Daily login")

    assert db_module.get_user_coins(uid) == 1500


# ===========================================================================
# Upsert / match helpers
# ===========================================================================

def test_upsert_match_inserts_new():
    db_module.upsert_match(100, "Vietnam", "Thailand", "2026-06-15T14:00:00Z")
    m = db_module.get_match(100)
    assert m["team_a"] == "Vietnam"
    assert m["team_b"] == "Thailand"
    assert m["status"] == "Not Started"


def test_upsert_match_updates_existing():
    db_module.upsert_match(101, "Team A", "Team B", "2026-06-15T14:00:00Z")
    db_module.upsert_match(101, "Team A", "Team C", "2026-06-15T14:00:00Z",
                           status="Finished", result="A_win")
    m = db_module.get_match(101)
    assert m["team_b"] == "Team C"
    assert m["status"] == "Finished"
    assert m["result"] == "A_win"


def test_get_matches_by_date():
    db_module.upsert_match(1, "A", "B", "2026-06-15T14:00:00Z")
    db_module.upsert_match(2, "C", "D", "2026-06-15T18:00:00Z")
    db_module.upsert_match(3, "E", "F", "2026-06-16T14:00:00Z")

    jun15 = db_module.get_matches_by_date("2026-06-15")
    assert len(jun15) == 2


def test_update_match_result():
    db_module.upsert_match(200, "Team X", "Team Y", "2026-06-15T14:00:00Z")
    db_module.update_match_result(200, "A_win")
    m = db_module.get_match(200)
    assert m["status"] == "Finished"
    assert m["result"] == "A_win"


# ===========================================================================
# Bets
# ===========================================================================

def test_place_bet_deducts_and_records():
    uid = db_module.register_user("+84666666666", "Frank")
    db_module.upsert_match(300, "Brazil", "Argentina", "2026-06-20T18:00:00Z")

    bet_id = db_module.place_bet(uid, 300, "A", 100)
    assert bet_id is not None

    assert db_module.get_user_coins(uid) == 900

    conn = db_module.get_connection()
    bet = conn.execute("SELECT * FROM bets WHERE bet_id = ?", (bet_id,)).fetchone()
    conn.close()
    assert bet["bet_choice"] == "A"
    assert bet["bet_amount"] == 100
    assert bet["status"] == "Pending"


def test_place_bet_rejects_non_multiple_of_10():
    uid = db_module.register_user("+84777777777", "Grace")
    db_module.upsert_match(301, "X", "Y", "2026-06-20T18:00:00Z")

    with pytest.raises(ValueError, match="multiple of 10"):
        db_module.place_bet(uid, 301, "A", 25)


def test_place_bet_rejects_zero_or_negative():
    uid = db_module.register_user("+84888888888", "Hank")
    db_module.upsert_match(302, "X", "Y", "2026-06-20T18:00:00Z")

    with pytest.raises(ValueError, match="multiple of 10"):
        db_module.place_bet(uid, 302, "A", 0)

    with pytest.raises(ValueError, match="multiple of 10"):
        db_module.place_bet(uid, 302, "A", -10)


def test_place_bet_rejects_insufficient_coins():
    uid = db_module.register_user("+84999999999", "Ivy")
    db_module.upsert_match(303, "X", "Y", "2026-06-20T18:00:00Z")

    with pytest.raises(ValueError, match="Insufficient"):
        db_module.place_bet(uid, 303, "A", 2000)


def test_place_bet_rejects_finished_match():
    uid = db_module.register_user("+84000000000", "Jack")
    db_module.upsert_match(304, "X", "Y", "2026-06-20T18:00:00Z",
                           status="Finished", result="A_win")

    with pytest.raises(ValueError, match="finished match"):
        db_module.place_bet(uid, 304, "A", 100)


def test_place_bet_rejects_nonexistent_match():
    uid = db_module.register_user("+84101010101", "Kate")

    with pytest.raises(ValueError, match="Match not found"):
        db_module.place_bet(uid, 99999, "A", 100)


def test_place_bet_rejects_nonexistent_user():
    with pytest.raises(ValueError, match="User not found"):
        db_module.place_bet(999, 300, "A", 100)


# ===========================================================================
# Settle bets
# ===========================================================================

def test_settle_match_bets_a_win_pays_correctly():
    uid_a = db_module.register_user("+84a00000001", "Alice")
    uid_b = db_module.register_user("+84b00000001", "Bob")
    uid_draw = db_module.register_user("+84d00000001", "Dave")
    db_module.upsert_match(400, "Home", "Away", "2026-06-25T18:00:00Z")

    db_module.place_bet(uid_a, 400, "A", 100)     # Alice bets Home win
    db_module.place_bet(uid_b, 400, "B", 50)       # Bob bets Away win
    db_module.place_bet(uid_draw, 400, "DRAW", 30)  # Dave bets Draw

    db_module.settle_match_bets(400, "A_win")

    # Alice should get 2x = 200 coins
    assert db_module.get_user_coins(uid_a) == 1100  # 1000 - 100 + 200

    # Bob lost
    assert db_module.get_user_coins(uid_b) == 950   # 1000 - 50

    # Dave lost
    assert db_module.get_user_coins(uid_draw) == 970  # 1000 - 30

    conn = db_module.get_connection()
    alice_bet = conn.execute(
        "SELECT status FROM bets WHERE user_id = ? AND match_id = 400", (uid_a,)
    ).fetchone()
    bob_bet = conn.execute(
        "SELECT status FROM bets WHERE user_id = ? AND match_id = 400", (uid_b,)
    ).fetchone()
    conn.close()
    assert alice_bet["status"] == "Won"
    assert bob_bet["status"] == "Lost"


def test_settle_match_bets_draw_pays_draw_bettors():
    uid_a = db_module.register_user("+84a00000002", "A2")
    uid_d = db_module.register_user("+84d00000002", "D2")
    db_module.upsert_match(401, "Home", "Away", "2026-06-26T18:00:00Z")

    db_module.place_bet(uid_a, 401, "A", 100)
    db_module.place_bet(uid_d, 401, "DRAW", 100)

    db_module.settle_match_bets(401, "Draw")

    assert db_module.get_user_coins(uid_a) == 900    # lost
    assert db_module.get_user_coins(uid_d) == 1100   # won: 1000 - 100 + 200


def test_settle_match_bets_updates_match_status():
    db_module.upsert_match(402, "H", "A", "2026-06-27T18:00:00Z")
    db_module.settle_match_bets(402, "B_win")
    m = db_module.get_match(402)
    assert m["status"] == "Finished"
    assert m["result"] == "B_win"


# ===========================================================================
# Leaderboard
# ===========================================================================

def test_get_leaderboard_orders_by_coins_desc():
    uid1 = db_module.register_user("+84l00000001", "First")
    uid2 = db_module.register_user("+84l00000002", "Second")
    uid3 = db_module.register_user("+84l00000003", "Third")

    db_module.add_coins(uid2, 500, "mission", "bonus")
    db_module.add_coins(uid1, 100, "mission", "bonus")

    lb = db_module.get_leaderboard()
    assert lb[0]["full_name"] == "Second"   # 1500
    assert lb[1]["full_name"] == "First"    # 1100
    assert lb[2]["full_name"] == "Third"    # 1000


# ===========================================================================
# Missions
# ===========================================================================

def test_complete_mission_adds_coins_and_logs():
    uid = db_module.register_user("+84m00000001", "MissionUser")
    db_module.complete_mission(uid, "daily_login", 20)

    assert db_module.get_user_coins(uid) == 1020

    conn = db_module.get_connection()
    logs = conn.execute(
        "SELECT * FROM mission_logs WHERE user_id = ?", (uid,)
    ).fetchall()
    conn.close()
    assert len(logs) == 1
    assert logs[0]["mission_type"] == "daily_login"
    assert logs[0]["reward_coins"] == 20


def test_complete_mission_daily_limit_is_query_side():
    """The app checks DATE(completed_at) before calling complete_mission.
       The DB function itself does not enforce the limit — it's query-side."""
    uid = db_module.register_user("+84m00000002", "M2")
    db_module.complete_mission(uid, "daily_login", 20)
    db_module.complete_mission(uid, "daily_login", 20)

    # Both go through — enforcement is in the caller (the app checks first)
    assert db_module.get_user_coins(uid) == 1040

    conn = db_module.get_connection()
    logs = conn.execute(
        "SELECT COUNT(*) as cnt FROM mission_logs WHERE user_id = ?", (uid,)
    ).fetchone()
    conn.close()
    assert logs["cnt"] == 2


# ===========================================================================
# Daily penalty
# ===========================================================================

def test_apply_daily_penalty_on_day_with_no_matches_does_nothing():
    db_module.register_user("+84p00000001", "Penalty1")
    penalized = db_module.apply_daily_penalty("2026-06-01")
    assert penalized == 0
    assert db_module.get_user_coins(1) == 1000


def test_apply_daily_penalty_when_user_did_not_bet():
    uid = db_module.register_user("+84p00000002", "Penalty2")
    db_module.upsert_match(500, "A", "B", "2026-06-10T14:00:00Z")

    penalized = db_module.apply_daily_penalty("2026-06-10")
    assert penalized == 1
    # Penalty is 10% of 1000 = 100
    assert db_module.get_user_coins(uid) == 900


def test_apply_daily_penalty_spares_user_who_bet():
    uid = db_module.register_user("+84p00000003", "Penalty3")
    db_module.upsert_match(501, "A", "B", "2026-06-11T14:00:00Z")
    db_module.place_bet(uid, 501, "A", 100)

    # Force the bet's created_at to match the match date so the penalty check sees it
    conn = db_module.get_connection()
    conn.execute("UPDATE bets SET created_at = '2026-06-11 10:00:00' WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()

    penalized = db_module.apply_daily_penalty("2026-06-11")
    assert penalized == 0
    # Only lost the bet amount, not penalized
    assert db_module.get_user_coins(uid) == 900


def test_apply_daily_penalty_rounds_up_to_multiple_of_10():
    uid = db_module.register_user("+84p00000004", "Penalty4")
    # Set coins to an odd amount
    conn = db_module.get_connection()
    conn.execute("UPDATE users SET current_coins = 1050 WHERE id = ?", (uid,))
    conn.commit()
    conn.close()

    db_module.upsert_match(502, "A", "B", "2026-06-12T14:00:00Z")
    penalized = db_module.apply_daily_penalty("2026-06-12")
    assert penalized == 1
    # 10% of 1050 = 105, rounded up to 110
    assert db_module.get_user_coins(uid) == 940


def test_apply_daily_penalty_with_small_balance_still_deducts_minimum():
    uid = db_module.register_user("+84p00000005", "Penalty5")
    conn = db_module.get_connection()
    conn.execute("UPDATE users SET current_coins = 5 WHERE id = ?", (uid,))
    conn.commit()
    conn.close()

    db_module.upsert_match(503, "A", "B", "2026-06-13T14:00:00Z")
    penalized = db_module.apply_daily_penalty("2026-06-13")
    assert penalized == 1
    # min(10, 5) = 5 — shouldn't go below 0
    assert db_module.get_user_coins(uid) == 0


# ===========================================================================
# Sync matches from API
# ===========================================================================

def test_sync_matches_from_api(mocker):
    mock_data = {
        "matches": [
            {
                "id": 600,
                "homeTeam": {"name": "Vietnam"},
                "awayTeam": {"name": "Thailand"},
                "utcDate": "2026-06-15T14:00:00Z",
                "status": "SCHEDULED",
            },
            {
                "id": 601,
                "homeTeam": {"name": "Brazil"},
                "awayTeam": {"name": "Argentina"},
                "utcDate": "2026-06-15T18:00:00Z",
                "status": "FINISHED",
                "score": {"fullTime": {"home": 2, "away": 1}},
            },
        ]
    }
    mocker.patch("world_cup.api.fetch_matches", return_value=mock_data)

    n = db_module.sync_matches_from_api()
    assert n == 2

    m1 = db_module.get_match(600)
    assert m1["team_a"] == "Vietnam"
    assert m1["status"] == "Not Started"

    m2 = db_module.get_match(601)
    assert m2["status"] == "Finished"
    assert m2["result"] == "A_win"


def test_sync_matches_from_api_empty_list(mocker):
    mocker.patch("world_cup.api.fetch_matches", return_value={"matches": []})
    n = db_module.sync_matches_from_api()
    assert n == 0
