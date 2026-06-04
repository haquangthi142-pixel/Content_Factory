"""Pure game logic — no DB, no Streamlit, no I/O. Testable with plain data."""

# ---------------------------------------------------------------------------
# Bet validation
# ---------------------------------------------------------------------------

def validate_bet_amount(amount: int) -> tuple[bool, str | None]:
    """Check if a bet amount is valid (positive multiple of 10)."""
    if amount <= 0 or amount % 10 != 0:
        return False, "Bet amount must be a positive multiple of 10"
    return True, None


def validate_bet(user_coins: int, match_status: str, bet_amount: int) -> tuple[bool, str | None]:
    """Full pre-bet validation: amount, affordability, match eligiblity."""
    ok, err = validate_bet_amount(bet_amount)
    if not ok:
        return False, err
    if user_coins < bet_amount:
        return False, f"Insufficient coins. You have {user_coins}."
    if match_status == "Finished":
        return False, "Cannot bet on a finished match"
    return True, None


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

BET_WIN_CONDITIONS = {
    "A": "A_win",
    "B": "B_win",
    "DRAW": "Draw",
}


def is_bet_won(bet_choice: str, match_result: str) -> bool:
    """Determine if a 1X2 bet wins given the match result."""
    return BET_WIN_CONDITIONS.get(bet_choice) == match_result


WIN_FEE_PERCENT = 5  # house fee on winning payouts


def settle_bet(bet_choice: str, bet_amount: int, match_result: str) -> tuple[str, int]:
    """Return (new_status, payout_amount) for a settled bet.

    Winning payout = bet_amount * 2, minus WIN_FEE_PERCENT of the gross.
    Example: bet 100 → gross 200 → fee 10 → net payout 190.
    """
    if is_bet_won(bet_choice, match_result):
        gross = bet_amount * 2
        fee = int(gross * WIN_FEE_PERCENT / 100)
        return "Won", gross - fee
    return "Lost", 0


# ---------------------------------------------------------------------------
# Handicap payouts
# ---------------------------------------------------------------------------

HANDICAP_PAYOUT = {0.5: 1.8, 1.5: 2.5, 2.5: 3.5, 3.5: 5.0}


def get_handicap_payout(line: float) -> float:
    return HANDICAP_PAYOUT.get(line, 1.0)


def calc_handicap_win_amount(bet_amount: int, handicap_line: float, fee_percent: int) -> int:
    """Payout for a winning handicap bet (fee deducted from stake first)."""
    fee = int(bet_amount * fee_percent / 100)
    net_stake = bet_amount - fee
    multiplier = get_handicap_payout(handicap_line)
    return int(net_stake * multiplier)


# ---------------------------------------------------------------------------
# Daily penalty
# ---------------------------------------------------------------------------

def calc_penalty_amount(current_coins: int) -> int:
    """10% of coins, rounded up to multiple of 10, minimum 10 coins."""
    penalty = max(10, current_coins // 10)
    if penalty % 10 != 0:
        penalty = ((penalty // 10) + 1) * 10
    if penalty > current_coins:
        penalty = current_coins
    return penalty


def calc_users_to_penalize(users: list[dict], user_ids_who_bet: set[int]) -> list[dict]:
    """Given all users and the set of user IDs who bet, return users to penalize."""
    result = []
    for u in users:
        if u["id"] in user_ids_who_bet:
            continue
        penalty = calc_penalty_amount(u["current_coins"])
        if penalty > 0:
            result.append({**u, "penalty": penalty})
    return result


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

MISSION_REWARDS = {
    "share_facebook": 50,
    "daily_login": 20,
    "invite_friend": 100,
}


def get_mission_reward(mission_type: str) -> int:
    """Return the coin reward for a mission type."""
    return MISSION_REWARDS.get(mission_type, 0)


def is_mission_already_done(mission_logs_today: int) -> bool:
    """Check if a mission was already completed today."""
    return mission_logs_today > 0
