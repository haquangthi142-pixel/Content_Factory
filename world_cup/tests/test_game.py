import pytest
from world_cup import game


# ===========================================================================
# validate_bet_amount
# ===========================================================================

def test_validate_bet_amount_accepts_multiple_of_10():
    ok, err = game.validate_bet_amount(100)
    assert ok
    assert err is None


def test_validate_bet_amount_rejects_non_multiple_of_10():
    ok, err = game.validate_bet_amount(25)
    assert not ok
    assert "multiple of 10" in err


def test_validate_bet_amount_rejects_zero():
    ok, err = game.validate_bet_amount(0)
    assert not ok


def test_validate_bet_amount_rejects_negative():
    ok, err = game.validate_bet_amount(-10)
    assert not ok


# ===========================================================================
# validate_bet
# ===========================================================================

def test_validate_bet_ok():
    ok, err = game.validate_bet(user_coins=500, match_status="Not Started", bet_amount=100)
    assert ok
    assert err is None


def test_validate_bet_rejects_insufficient_coins():
    ok, err = game.validate_bet(user_coins=50, match_status="Not Started", bet_amount=100)
    assert not ok
    assert "Insufficient" in err


def test_validate_bet_rejects_finished_match():
    ok, err = game.validate_bet(user_coins=500, match_status="Finished", bet_amount=100)
    assert not ok
    assert "finished match" in err


def test_validate_bet_rejects_bad_amount():
    ok, err = game.validate_bet(user_coins=500, match_status="Not Started", bet_amount=25)
    assert not ok
    assert "multiple of 10" in err


# ===========================================================================
# is_bet_won
# ===========================================================================

def test_is_bet_won_a_win():
    assert game.is_bet_won("A", "A_win") is True
    assert game.is_bet_won("B", "A_win") is False
    assert game.is_bet_won("DRAW", "A_win") is False


def test_is_bet_won_b_win():
    assert game.is_bet_won("B", "B_win") is True
    assert game.is_bet_won("A", "B_win") is False


def test_is_bet_won_draw():
    assert game.is_bet_won("DRAW", "Draw") is True
    assert game.is_bet_won("A", "Draw") is False


# ===========================================================================
# settle_bet
# ===========================================================================

def test_settle_bet_won():
    status, payout = game.settle_bet("A", 100, "A_win")
    assert status == "Won"
    assert payout == 190  # gross 200, minus 5% fee (10)


def test_settle_bet_lost():
    status, payout = game.settle_bet("B", 50, "A_win")
    assert status == "Lost"
    assert payout == 0


def test_settle_bet_draw():
    status, payout = game.settle_bet("DRAW", 30, "Draw")
    assert status == "Won"
    assert payout == 57  # gross 60, minus 5% fee (3)


# ===========================================================================
# handicap
# ===========================================================================

def test_get_handicap_payout_known():
    assert game.get_handicap_payout(0.5) == 1.8
    assert game.get_handicap_payout(3.5) == 5.0


def test_get_handicap_payout_unknown_falls_back():
    assert game.get_handicap_payout(99.0) == 1.0


def test_calc_handicap_win_amount():
    # stake=100, fee=5 -> fee_amount=5, net=95, multiplier=1.8 -> 171
    amount = game.calc_handicap_win_amount(100, 0.5, 5)
    assert amount == 171



# ===========================================================================
# missions
# ===========================================================================

def test_get_mission_reward():
    assert game.get_mission_reward("daily_login") == 20
    assert game.get_mission_reward("invite_friend") == 100


def test_get_mission_reward_unknown():
    assert game.get_mission_reward("nonexistent") == 0


def test_is_mission_already_done():
    assert game.is_mission_already_done(1) is True
    assert game.is_mission_already_done(0) is False
