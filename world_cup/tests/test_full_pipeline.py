"""End-to-end pipeline test: seed → bet → settle → verify.

Run directly:
    python world_cup/tests/test_full_pipeline.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from world_cup import db, game


def banner(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def reset_db():
    """Wipe and re-init the database for a clean test."""
    db_path = db.DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    db.init_db()
    print("[OK] Database reset complete")


def seed_data():
    """Create test users and mock matches."""
    # -- Users --
    u1 = db.register_user("+8490111222", "Alice Test")
    u2 = db.register_user("+8490111333", "Bob Test")
    print(f"[OK] Users: Alice id={u1}, Bob id={u2}")

    # -- Matches --
    matches = [
        # (id, team_a, team_b, match_time, status)
        (100, "Vietnam", "Thailand", "2026-06-12T14:00:00Z", "Not Started"),
        (101, "Brazil", "Argentina", "2026-06-12T18:00:00Z", "Not Started"),
        (102, "France", "Germany", "2026-06-13T20:00:00Z", "Not Started"),
    ]
    for mid, ta, tb, mt, st in matches:
        db.admin_insert_match(mid, ta, tb, mt, st)
    print(f"[OK] Matches: {len(matches)} created")
    return u1, u2


def place_bets(u1, u2):
    """Place test bets covering win/lose/draw scenarios."""
    bets = []

    # Alice: bet on Vietnam win (match 100)
    bid = db.place_bet(u1, 100, "A", 100)
    bets.append(("Alice", bid, 100, "A", "Vietnam vs Thailand"))
    print(f"  Alice → {100} coins on Vietnam Win  (bet #{bid})")

    # Bob: bet on Draw (match 100) - opposite choice
    bid = db.place_bet(u2, 100, "DRAW", 50)
    bets.append(("Bob", bid, 100, "DRAW", "Vietnam vs Thailand"))
    print(f"  Bob   → {50} coins on Draw           (bet #{bid})")

    # Alice: bet on Brazil win (match 101)
    bid = db.place_bet(u1, 101, "A", 200)
    bets.append(("Alice", bid, 101, "A", "Brazil vs Argentina"))
    print(f"  Alice → {200} coins on Brazil Win  (bet #{bid})")

    # Bob: bet on Argentina win (match 101)
    bid = db.place_bet(u2, 101, "B", 100)
    bets.append(("Bob", bid, 101, "B", "Brazil vs Argentina"))
    print(f"  Bob   → {100} coins on Argentina Win (bet #{bid})")

    # Alice: bet on France vs Germany draw (match 102)
    bid = db.place_bet(u1, 102, "DRAW", 150)
    bets.append(("Alice", bid, 102, "DRAW", "France vs Germany"))
    print(f"  Alice → {150} coins on Draw          (bet #{bid})")

    return bets


def settle_and_verify(u1, u2):
    """Settle matches and verify payouts."""
    alice = db.get_user(u1)
    bob = db.get_user(u2)
    print(f"\nBalances before settlement:")
    print(f"  Alice: {alice['current_coins']} coins")
    print(f"  Bob:   {bob['current_coins']} coins")

    # -- Settle match 100: Vietnam wins (A_win) --
    banner("Settle Match #100: Vietnam vs Thailand → A_win")
    db.settle_match_bets(100, "A_win")

    print("Settled! Checking results...")
    # Alice bet 100 on A → should win 200
    # Bob bet 50 on DRAW → should lose
    _show_bet_results(100)
    _show_user_coins(u1, u2)

    # -- Settle match 101: Brazil wins (A_win) --
    banner("Settle Match #101: Brazil vs Argentina → A_win")
    db.settle_match_bets(101, "A_win")

    print("Settled! Checking results...")
    # Alice bet 200 on A → should win 400
    # Bob bet 100 on B → should lose
    _show_bet_results(101)
    _show_user_coins(u1, u2)

    # -- Settle match 102: Draw --
    banner("Settle Match #102: France vs Germany → Draw")
    db.settle_match_bets(102, "Draw")

    print("Settled! Checking results...")
    # Alice bet 150 on DRAW → should win 300
    _show_bet_results(102)
    _show_user_coins(u1, u2)


def _show_bet_results(match_id):
    """Print bet outcomes for a match."""
    conn = db.get_connection()
    bets = conn.execute(
        """SELECT b.*, u.full_name FROM bets b
           JOIN users u ON b.user_id = u.id
           WHERE b.match_id = ?""", (match_id,)
    ).fetchall()
    conn.close()
    for b in bets:
        emoji = "[WIN]" if b["status"] == "Won" else "[LOST]"
        print(f"  {emoji} {b['full_name']}: bet {b['bet_amount']} on {b['bet_choice']} → {b['status']}")


def _show_user_coins(u1, u2):
    """Print current balances."""
    a = db.get_user(u1)
    b = db.get_user(u2)
    print(f"  $ Alice: {a['current_coins']} coins")
    print(f"  $ Bob:   {b['current_coins']} coins")


def show_transactions():
    """Print all coin transactions."""
    banner("Transaction History")
    txs = db.admin_get_all_transactions()
    for t in txs:
        sign = "+" if t["amount"] > 0 else ""
        print(f"  #{t['tx_id']:03d} {t['user_name']:12s} {sign}{t['amount']:>5d}  {t['type']:10s}  {t['description']}")


def show_final_summary(u1, u2):
    """Recap expected vs actual."""
    banner("Final Summary")

    alice = db.get_user(u1)
    bob = db.get_user(u2)

    # Alice started: 1000, bet 100+200+150=450, won 200+400+300=900. Net: 1000-450+900=1450
    # Bob started:   1000, bet 50+100=150, won 0.                     Net: 1000-150=850
    print("Expected:")
    print("  Alice: 1000 - 450 (bets) + 900 (payouts) = 1450 coins")
    print("  Bob:   1000 - 150 (bets) + 0   (payouts) = 850 coins")
    print(f"\nActual:")
    print(f"  Alice: {alice['current_coins']} coins {'[WIN]' if alice['current_coins'] == 1450 else '[LOST] MISMATCH'}")
    print(f"  Bob:   {bob['current_coins']} coins {'[WIN]' if bob['current_coins'] == 850 else '[LOST] MISMATCH'}")

    conn = db.get_connection()
    bets = conn.execute("SELECT status, COUNT(*) as cnt FROM bets GROUP BY status").fetchall()
    conn.close()
    outcome_strs = [f"{b['cnt']} {b['status']}" for b in bets]
    print(f"\nBet outcomes: {', '.join(outcome_strs)}")


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    banner("FULL PIPELINE TEST")
    reset_db()

    banner("1. SEED DATA")
    u1, u2 = seed_data()

    banner("2. PLACE BETS")
    place_bets(u1, u2)

    banner("3. SETTLE MATCHES")
    settle_and_verify(u1, u2)

    show_transactions()
    show_final_summary(u1, u2)

    print("\n[WIN] Pipeline test complete!\n")
