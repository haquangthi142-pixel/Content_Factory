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

HANDICAP_PAYOUT = 2.0  # flat 2× payout for all handicap lines


def get_handicap_payout(line: float) -> float:
    return HANDICAP_PAYOUT


def calc_handicap_win_amount(bet_amount: int, handicap_line: float, fee_percent: int) -> int:
    """Payout for a winning handicap bet: 2× stake minus fee on stake."""
    fee = int(bet_amount * fee_percent / 100)
    net_stake = bet_amount - fee
    return net_stake * 2


def settle_handicap_bet(handicap_side: str, handicap_line: float,
                         handicap_favorite: str, score_a: int | None, score_b: int | None,
                         bet_amount: int, handicap_fee: int) -> tuple[str, int]:
    """Return (status, payout) for a handicap bet.

    handicap_side: 'favorite' or 'underdog'
    handicap_favorite: 'A' or 'B' (which team is the favorite)
    handicap_line: spread (e.g. 0.5, 1.5, 2.5)
    score_a / score_b: final scores; if None the bet stays Pending.
    """
    if score_a is None or score_b is None:
        return ("Pending", 0)

    if handicap_favorite == "A":
        fav_score, und_score = score_a, score_b
    else:
        fav_score, und_score = score_b, score_a

    # Favorite covers the spread if (fav_score - line) > underdog_score
    favorite_covers = (fav_score - handicap_line) > und_score

    if handicap_side == "favorite":
        won = favorite_covers
    else:
        won = not favorite_covers

    if won:
        payout = calc_handicap_win_amount(bet_amount, handicap_line, handicap_fee)
        return ("Won", payout)
    return ("Lost", 0)


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
