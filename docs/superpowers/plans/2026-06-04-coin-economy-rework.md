# Coin Economy Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 1000-coin starting capital with 10 free coins + admin buy-coins system (VND/1000 = coins, min 100K VND). Remove daily penalty.

**Architecture:** DB schema change (DEFAULT 10), new `purchases` table, admin panel buy-coins form. Pure game logic (game.py) loses penalty functions. All test expectations updated from 1000→10.

**Tech Stack:** Python 3.11, Streamlit, SQLite, pytest

---

### Task 1: Update game.py — remove penalty functions

**Files:**
- Modify: `world_cup/game.py`

- [ ] **Step 1: Delete penalty functions and constants**

Remove lines 71-98 from `game.py` (everything from `def calc_penalty_amount` through the end of `calc_users_to_penalize`). The file should end after the `get_mission_reward` and `is_mission_already_done` functions.

Before (lines 71-98):
```python
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
```

Delete those lines entirely. The file should go directly from missions section to nothing (the missions section stays).

- [ ] **Step 2: Verify no leftover penalty imports**

Run: `Select-String -Path world_cup/game.py -Pattern "penalty"`

Should return nothing.

- [ ] **Step 3: Commit**

```bash
git add world_cup/game.py
git commit -m "refactor: remove daily penalty functions from game.py"
```

---

### Task 2: Update db.py — change default coins, remove penalty, add purchase

**Files:**
- Modify: `world_cup/db.py`

- [ ] **Step 1: Change DEFAULT 1000 to DEFAULT 10 in users table**

```python
# Line 24 — change DEFAULT value
current_coins   INTEGER NOT NULL DEFAULT 10,
```

- [ ] **Step 2: Change register_user to give 10 coins**

```python
# Line 97 — change INSERT value
conn.execute(
    "INSERT INTO users (phone, full_name, current_coins) VALUES (?, ?, 10)",
    (phone, full_name),
)
conn.execute(
    "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, 10, 'free_trial', 'Free trial coins')",
    (user_id,),
)
```

- [ ] **Step 3: Remove apply_daily_penalty function**

Delete the entire `apply_daily_penalty` function (lines 424-464 in current file). Everything from:
```python
def apply_daily_penalty(date_str: str):
    """Deduct 10% from users who didn't bet on a match day."""
    ...
```
through the `finally: conn.close()` block.

- [ ] **Step 4: Add purchase_coins function**

Add after the missions section (before the Admin CRUD section):

```python
def purchase_coins(user_id: int, vnd_amount: int) -> int:
    """Convert VND to coins and credit user. Returns coins credited."""
    coins = vnd_amount // 1000
    if coins <= 0:
        raise ValueError(f"Minimum purchase is 100,000 VND (100 coins). Got {vnd_amount:,} VND.")
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET current_coins = current_coins + ? WHERE id = ?",
                     (coins, user_id))
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, 'purchase', ?)",
            (user_id, coins, f"Purchased {coins} coins ({vnd_amount:,} VND)"),
        )
        conn.commit()
        return coins
    finally:
        conn.close()
```

- [ ] **Step 5: Add admin_get_purchases function**

```python
def admin_get_purchases():
    """Return all purchase transactions (admin-only view)."""
    conn = get_connection()
    try:
        return _dict_rows(conn.execute(
            """SELECT t.*, u.full_name AS user_name
               FROM coin_transactions t
               JOIN users u ON t.user_id = u.id
               WHERE t.type = 'purchase'
               ORDER BY t.created_at DESC"""
        ).fetchall())
    finally:
        conn.close()
```

- [ ] **Step 6: Update bet validation message to mention purchasing**

In `place_bet`, line 307, change the error message:
```python
raise ValueError(f"Insufficient coins. You have {coins['current_coins']}. Contact admin to purchase more.")
```

- [ ] **Step 7: Commit**

```bash
git add world_cup/db.py
git commit -m "feat: 10 free coins, remove penalty, add purchase_coins"
```

---

### Task 3: Update admin.py — add buy-coins form and purchase history

**Files:**
- Modify: `world_cup/admin.py`

- [ ] **Step 1: Change add-user default coins to 10**

Line 87:
```python
coins = st.number_input("Starting Coins", min_value=0, value=10, step=10)
```

- [ ] **Step 2: Add "Buy Coins" section to _render_users**

After the "Edit / Delete User" section, add:

```python
    st.markdown("---")
    st.markdown("#### Buy Coins (VND → Coins)")
    buy_user_id = st.selectbox("Player", user_ids, key="buy_coins_user")
    buy_vnd = st.number_input(
        "VND Amount",
        min_value=100000,
        value=100000,
        step=100000,
        key="buy_vnd",
        help="1,000 VND = 1 coin. Min 100,000 VND."
    )
    buy_coins = buy_vnd // 1000
    st.caption(f"Coins to credit: **{buy_coins}** ({buy_vnd:,} VND)")
    if st.button("Credit Coins", key="buy_coins_btn"):
        try:
            credited = db.purchase_coins(buy_user_id, buy_vnd)
            st.success(f"Credited {credited} coins to user #{buy_user_id}")
            st.rerun()
        except ValueError as e:
            st.error(str(e))
```

- [ ] **Step 3: Add "Purchases" tab to admin**

Add a new tab "Purchases" in `render_admin` (after Transactions tab):

```python
    tabs = st.tabs(["Users", "Matches", "Bets", "Transactions", "Purchases", "Missions"])
```

Add tab handler after the Transactions tab:
```python
    with tabs[4]:
        _render_purchases()
```

And update the Missions tab index:
```python
    with tabs[5]:
        _render_missions()
```

- [ ] **Step 4: Add _render_purchases function**

```python
def _render_purchases():
    st.subheader("Coin Purchases")
    purchases = db.admin_get_purchases()

    if not purchases:
        st.info("No purchases yet.")
        return

    st.caption(f"{len(purchases)} purchases")
    display_cols = ["tx_id", "user_name", "amount", "description", "created_at"]
    st.dataframe(
        [{k: p[k] for k in display_cols} for p in purchases],
        use_container_width=True, hide_index=True,
    )
```

- [ ] **Step 5: Commit**

```bash
git add world_cup/admin.py
git commit -m "feat: admin buy-coins form + purchase history tab"
```

---

### Task 4: Update betting_ui.py — out-of-coins message

**Files:**
- Modify: `world_cup/betting_ui.py`

- [ ] **Step 1: No code changes needed — the bet validation error in db.py already says "Contact admin to purchase more."**

The `place_bet` function in db.py already raises the correct message (changed in Task 2).

However, let's verify the UI doesn't have any hardcoded 1000-coin references. Search: `Select-String -Path world_cup/betting_ui.py -Pattern "1000"` — should return nothing.

No changes needed in this file.

- [ ] **Step 2: Commit (if no changes)**

```bash
# Nothing to commit for this task
```

---

### Task 5: Update game.py tests — remove penalty tests, no value changes

**Files:**
- Modify: `world_cup/tests/test_game.py`

- [ ] **Step 1: Delete penalty test functions**

Remove lines 121-167 (all penalty tests):
- `test_calc_penalty_standard`
- `test_calc_penalty_rounds_up_to_multiple_of_10`
- `test_calc_penalty_minimum_10`
- `test_calc_penalty_small_balance_caps_at_balance`
- `test_calc_users_to_penalize`
- `test_calc_users_to_penalize_everyone_bets`
- `test_calc_users_to_penalize_empty`

- [ ] **Step 2: Run tests to verify**

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -m pytest world_cup/tests/test_game.py -v
```

Expected: 20 passed (27 - 7 penalty tests)

- [ ] **Step 3: Commit**

```bash
git add world_cup/tests/test_game.py
git commit -m "test: remove penalty tests from test_game.py"
```

---

### Task 6: Update db.py tests — 1000→10 + remove penalty tests

**Files:**
- Modify: `world_cup/tests/test_db.py`

- [ ] **Step 1: Update 1000 to 10 in test_register_user_creates_user_with_starting_coins**

Line 60:
```python
assert user["current_coins"] == 10
```

Line 70:
```python
assert txs[0]["amount"] == 10
assert txs[0]["type"] == "free_trial"
```

- [ ] **Step 2: Update test_get_user_coins**

Line 94:
```python
assert db_module.get_user_coins(uid) == 10
```

- [ ] **Step 3: Recalculate and update settlement tests**

All settlement tests need values recalculated from base 10 coins.

`test_settle_match_bets_a_win_pays_correctly`:
```python
# Alice: 10 - 100 -> rejected (insufficient)! Need to give coins first
# Add coins to Alice so she can bet
conn = db_module.get_connection()
conn.execute("UPDATE users SET current_coins = 1000 WHERE id = ?", (uid_a,))
conn.commit()
conn.close()
# ... then place bets and settle normally
assert db_module.get_user_coins(uid_a) == 1090  # 1000 - 100 + 190
```

Actually, simpler approach: make the tests independent of starting amount by giving explicit coin amounts before betting.

For `test_settle_match_bets_a_win_pays_correctly`:
```python
import sqlite3

def test_settle_match_bets_a_win_pays_correctly():
    uid_a = db_module.register_user("+84a00000001", "Alice")
    uid_b = db_module.register_user("+84b00000001", "Bob")
    uid_draw = db_module.register_user("+84d00000001", "Dave")
    db_module.upsert_match(400, "Home", "Away", "2026-06-25T18:00:00Z")

    # Give each user 1000 coins via admin to set a known baseline
    conn = db_module.get_connection()
    for uid in [uid_a, uid_b, uid_draw]:
        conn.execute("UPDATE users SET current_coins = 1000 WHERE id = ?", (uid,))
    conn.commit()
    conn.close()

    db_module.place_bet(uid_a, 400, "A", 100)
    db_module.place_bet(uid_b, 400, "B", 50)
    db_module.place_bet(uid_draw, 400, "DRAW", 30)

    db_module.settle_match_bets(400, "A_win")

    # Alice: 1000 - 100 + 190 (gross 200 - 5% fee 10)
    assert db_module.get_user_coins(uid_a) == 1090
    # Bob lost: 1000 - 50
    assert db_module.get_user_coins(uid_b) == 950
    # Dave lost: 1000 - 30
    assert db_module.get_user_coins(uid_draw) == 970
```

Do the same pattern for `test_settle_match_bets_draw_pays_draw_bettors` — give 1000 coins baseline.

- [ ] **Step 4: Remove penalty tests**

Delete these test functions:
- `test_apply_daily_penalty_on_day_with_no_matches_does_nothing`
- `test_apply_daily_penalty_when_user_did_not_bet`
- `test_apply_daily_penalty_spares_user_who_bet`
- `test_apply_daily_penalty_rounds_up_to_multiple_of_10`
- `test_apply_daily_penalty_with_small_balance_still_deducts_minimum`

- [ ] **Step 5: Update other tests that reference 1000 coins**

For `test_get_leaderboard_orders_by_coins_desc` (line 294-305):
```python
def test_get_leaderboard_orders_by_coins_desc():
    uid1 = db_module.register_user("+84leader001", "First")
    uid2 = db_module.register_user("+84leader002", "Second")
    uid3 = db_module.register_user("+84leader003", "Third")
    # Boost coins for testing
    db_module.add_coins(uid2, 500, "mission", "bonus")
    db_module.add_coins(uid1, 100, "mission", "bonus")
    lb = db_module.get_leaderboard()
    assert lb[0]["full_name"] == "Second"   # 10 + 500 = 510
    assert lb[1]["full_name"] == "First"    # 10 + 100 = 110
    assert lb[2]["full_name"] == "Third"    # 10
```

For `test_complete_mission_adds_coins_and_logs` (line 312):
```python
# uid starts with 10, gets +20 = 30
assert db_module.get_user_coins(uid) == 30
```

For line 336:
```python
assert db_module.get_user_coins(uid) == 50  # 30 + 20 = 50
```

For `test_place_multiple_bets_same_match` (line 471):
```python
# Give coins first
conn = db_module.get_connection()
conn.execute("UPDATE users SET current_coins = 1000 WHERE id = ?", (uid,))
conn.commit()
conn.close()
# Then place bets
assert db_module.get_user_coins(uid) == 820  # 1000 - 100 - 50 - 30
```

For `test_place_multiple_bets_mixed_markets` (line 495):
```python
# Give coins first
conn = db_module.get_connection()
conn.execute("UPDATE users SET current_coins = 1000 WHERE id = ?", (uid,))
conn.commit()
conn.close()
# Then place bets
assert db_module.get_user_coins(uid) == 800  # 1000 - 100 - 100
```

For `test_settle_multiple_bets_same_user` (line 520-521):
```python
# Give coins first
conn = db_module.get_connection()
conn.execute("UPDATE users SET current_coins = 1000 WHERE id = ?", (uid,))
conn.commit()
conn.close()
# Then place bets...
# Net: 1000 - 180 + 285 = 1105
assert db_module.get_user_coins(uid) == 1105
```

- [ ] **Step 6: Run db tests to verify**

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -m pytest world_cup/tests/test_db.py -v --ignore=test_db.py -k "not sync_matches"
```

Expected: All non-API-sync tests pass.

- [ ] **Step 7: Commit**

```bash
git add world_cup/tests/test_db.py
git commit -m "test: 1000->10 coins + remove penalty tests from test_db.py"
```

---

### Task 7: Update full pipeline test — 1000→10 baseline

**Files:**
- Modify: `world_cup/tests/test_full_pipeline.py`

- [ ] **Step 1: Give users coins after registration**

After `seed_data()` creates users (each with 10 coins), add coin top-ups so bets work:

In `seed_data`, after registering users, boost their coins:
```python
def seed_data():
    u1 = db.register_user("+8490111222", "Alice Test")
    u2 = db.register_user("+8490111333", "Bob Test")
    # Boost coins for testing
    conn = db.get_connection()
    conn.execute("UPDATE users SET current_coins = 1000 WHERE id = ?", (u1,))
    conn.execute("UPDATE users SET current_coins = 1000 WHERE id = ?", (u2,))
    conn.commit()
    conn.close()
    print(f"[OK] Users: Alice id={u1}, Bob id={u2} (1000 coins each)")
    ...
```

- [ ] **Step 2: Update expected values**

Comment lines 156 and 161 update to reflect 1000→1000 (unchanged since we boost). No change needed — the test already uses 1000 as baseline via the boost.

- [ ] **Step 3: Run test**

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python world_cup/tests/test_full_pipeline.py
```

Expected: All [WIN] assertions pass.

- [ ] **Step 4: Commit**

```bash
git add world_cup/tests/test_full_pipeline.py
git commit -m "test: boost coins in pipeline test (10 default -> 1000 baseline)"
```

---

### Task 8: Final verification — run all tests

- [ ] **Step 1: Run full test suite**

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -m pytest world_cup/tests/test_game.py world_cup/tests/test_db.py -v --ignore=test_db.py -k "not sync_matches"
```

Expected: All tests pass (0 failures)

- [ ] **Step 2: Run pipeline test**

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python world_cup/tests/test_full_pipeline.py
```

Expected: All [WIN] assertions pass

- [ ] **Step 3: Commit any remaining changes + push**

```bash
git status
git add -A
git commit -m "chore: final cleanup for coin economy rework"
git push
```
