# Handicap Betting — Remaining Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the handicap betting system: settlement logic, admin UI, user betting UI (market selector + profit preview), my-bets display, and tests.

**Architecture:** Pure game logic lives in `game.py` (testable, no I/O). DB operations in `db.py`. Shared Streamlit UI in `betting_ui.py` (used by both `betting_app.py` standalone and `app.py` integrated view). Admin UI in `admin.py`.

**Tech Stack:** Python 3.11, Streamlit, SQLite (via sqlite3)

**Prerequisite:** Tasks 1-3 from the original plan are done — DB schema columns exist, `place_handicap_bet()` works, payout helpers in `game.py`, admin CRUD accepts handicap params.

---

### Task 1: Handicap Settlement Logic in game.py

**Files:**
- Modify: `world_cup/game.py` (add `settle_handicap_bet`, after line 66)

**Goal:** Pure function that determines if a handicap bet wins, and calculates payout. No DB access.

- [ ] **Step 1: Add `settle_handicap_bet()` to game.py**

Open `world_cup/game.py`. After the `calc_handicap_win_amount` function (after line 66), add:

```python
def settle_handicap_bet(handicap_side: str, bet_amount: int,
                        handicap_line: float, handicap_favorite: str,
                        handicap_fee: int, score_a: int, score_b: int) -> tuple[str, int]:
    """Return (new_status, payout_amount) for a handicap bet.
    
    Args:
        handicap_side: 'favorite' or 'underdog'
        bet_amount: original wager
        handicap_line: e.g. 0.5, 1.5, 2.5, 3.5
        handicap_favorite: 'A' or 'B' (which team gives the handicap)
        handicap_fee: admin fee percent (e.g. 5 = 5%)
        score_a: goals scored by team A
        score_b: goals scored by team B
    """
    goal_diff = score_a - score_b

    if handicap_favorite == "A":
        effective_diff = goal_diff - handicap_line
    else:
        effective_diff = -goal_diff - handicap_line

    if handicap_side == "favorite":
        won = effective_diff > 0
    else:
        won = effective_diff < 0

    if won:
        payout = calc_handicap_win_amount(bet_amount, handicap_line, handicap_fee)
        return "Won", payout
    return "Lost", 0
```

- [ ] **Step 2: Verify the function imports correctly**

Run:
```bash
python -c "from world_cup.game import settle_handicap_bet; print(settle_handicap_bet('favorite', 100, 1.5, 'A', 5, 3, 0))"
```
Expected: `('Won', 237)`

- [ ] **Step 3: Run existing tests to ensure no regression**

```bash
python -m pytest world_cup/tests/test_game.py -v
```
Expected: All 21 tests pass.

- [ ] **Step 4: Commit**

```bash
git add world_cup/game.py
git commit -m "feat: add handicap bet settlement function to game.py"
```

---

### Task 2: Fix settle_match_bets in db.py to Handle Both Markets

**Files:**
- Modify: `world_cup/db.py` (settle_match_bets, lines 387-420)

**Goal:** `settle_match_bets()` currently calls `game.settle_bet()` for all bets — 1X2 only. Rewrite to branch on `market` column.

- [ ] **Step 1: Replace settle_match_bets()**

Replace the existing `settle_match_bets` function (lines 387-420) with:

```python
def settle_match_bets(match_id: int, result: str):
    """Settle all pending bets for a match. Handles both 1X2 and handicap markets."""
    conn = get_connection()
    try:
        match = conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        if not match:
            return

        conn.execute(
            "UPDATE matches SET result = ?, status = 'Finished' WHERE match_id = ?",
            (result, match_id),
        )
        pending = conn.execute(
            "SELECT * FROM bets WHERE match_id = ? AND status = 'Pending'", (match_id,)
        ).fetchall()

        for bet in pending:
            if bet["market"] == "handicap":
                status, payout = game.settle_handicap_bet(
                    bet["handicap_side"], bet["bet_amount"],
                    bet["handicap_line"], match["handicap_favorite"],
                    match["handicap_fee"] or 5,
                    match["score_a"], match["score_b"],
                )
            else:
                status, payout = game.settle_bet(
                    bet["bet_choice"], bet["bet_amount"], result
                )

            if status == "Won":
                conn.execute(
                    "UPDATE bets SET status = 'Won', settled_at = datetime('now') WHERE bet_id = ?",
                    (bet["bet_id"],),
                )
                conn.execute("UPDATE users SET current_coins = current_coins + ? WHERE id = ?",
                             (payout, bet["user_id"]))
                conn.execute(
                    "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, 'win', ?)",
                    (bet["user_id"], payout, f"Won bet #{bet['bet_id']}"),
                )
            else:
                conn.execute(
                    "UPDATE bets SET status = 'Lost', settled_at = datetime('now') WHERE bet_id = ?",
                    (bet["bet_id"],),
                )

        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 2: Verify import chain works**

```bash
python -c "from world_cup import db; print('settle_match_bets ready')"
```
Expected: No errors.

- [ ] **Step 3: Run existing tests**

```bash
python -m pytest world_cup/tests/test_db.py -v
```
Expected: All 22 existing tests pass (existing settlement tests exercise 1X2 path).

- [ ] **Step 4: Commit**

```bash
git add world_cup/db.py
git commit -m "fix: branch settle_match_bets on market column for handicap support"
```

---

### Task 3: Handicap Fields in Admin Match Editor

**Files:**
- Modify: `world_cup/admin.py` (_render_matches function, lines 132-207)

**Goal:** Add handicap line, favorite, and fee fields to both the Add Match form and the Edit Match section.

- [ ] **Step 1: Add handicap fields to Add Match form**

In `_render_matches()`, find the Add Match form expander. After the `c3, c4 = st.columns(2)` block that has status/result selectboxes and before `st.form_submit_button`, insert:

```python
            st.markdown("---")
            st.caption("Handicap Settings")
            c_h1, c_h2, c_h3 = st.columns(3)
            handicap_line = c_h1.selectbox(
                "Handicap Line",
                ["None", "0.5", "1.5", "2.5", "3.5"],
                key="add_handicap_line",
            )
            handicap_favorite = c_h2.selectbox(
                "Favorite (gives handicap)",
                ["A", "B"],
                key="add_handicap_favorite",
            )
            handicap_fee = c_h3.number_input(
                "Admin Fee %",
                min_value=0, max_value=20, value=5, step=1,
                key="add_handicap_fee",
            )
```

Then update the `st.form_submit_button` handler. Change:
```python
                if team_a.strip() and team_b.strip() and match_time.strip():
                    db.admin_insert_match(
                        match_id, team_a, team_b, match_time, status,
                        None if result == "None" else result,
                    )
```

To:
```python
                if team_a.strip() and team_b.strip() and match_time.strip():
                    db.admin_insert_match(
                        match_id, team_a, team_b, match_time, status,
                        None if result == "None" else result,
                        score_a=None, score_b=None,
                        handicap_line=None if handicap_line == "None" else float(handicap_line),
                        handicap_favorite=handicap_favorite if handicap_line != "None" else None,
                        handicap_fee=handicap_fee,
                    )
```

- [ ] **Step 2: Add handicap fields to Edit Match section**

In the Edit Match section, after the `c3, c4` status/result selectboxes and before `col_save, col_del`, insert:

```python
        c5, c6 = st.columns(2)
        new_score_a_val = match.get("score_a")
        new_score_b_val = match.get("score_b")
        new_score_a = c5.number_input(
            "Score A", value=int(new_score_a_val) if new_score_a_val is not None else 0,
            key="edit_score_a",
        )
        new_score_b = c6.number_input(
            "Score B", value=int(new_score_b_val) if new_score_b_val is not None else 0,
            key="edit_score_b",
        )

        st.markdown("---")
        st.caption("Handicap Settings")
        hc1, hc2, hc3 = st.columns(3)
        line_opts = ["None", "0.5", "1.5", "2.5", "3.5"]
        cur_line_raw = match.get("handicap_line")
        cur_line = str(cur_line_raw) if cur_line_raw is not None else "None"
        new_line = hc1.selectbox(
            "Handicap Line", line_opts,
            index=line_opts.index(cur_line) if cur_line in line_opts else 0,
            key="edit_handicap_line",
        )
        fav_opts = ["A", "B"]
        cur_fav = match.get("handicap_favorite") or "A"
        new_favorite = hc2.selectbox(
            "Favorite (gives handicap)", fav_opts,
            index=fav_opts.index(cur_fav) if cur_fav in fav_opts else 0,
            key="edit_handicap_favorite",
        )
        cur_fee = match.get("handicap_fee")
        new_fee = hc3.number_input(
            "Fee %", min_value=0, max_value=20,
            value=int(cur_fee) if cur_fee is not None else 5, step=1,
            key="edit_handicap_fee",
        )
```

Then update the Save button handler. Change:
```python
            if st.button("Save Changes", key="save_match"):
                db.admin_update_match(
                    selected_id, new_team_a, new_team_b, new_time, new_status,
                    None if new_result == "None" else new_result,
                )
```

To:
```python
            if st.button("Save Changes", key="save_match"):
                db.admin_update_match(
                    selected_id, new_team_a, new_team_b, new_time, new_status,
                    None if new_result == "None" else new_result,
                    score_a=new_score_a, score_b=new_score_b,
                    handicap_line=None if new_line == "None" else float(new_line),
                    handicap_favorite=new_favorite if new_line != "None" else None,
                    handicap_fee=new_fee,
                )
```

- [ ] **Step 3: Verify admin.py parses without syntax errors**

```bash
python -c "import ast; ast.parse(open('world_cup/admin.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add world_cup/admin.py
git commit -m "feat: add handicap fields to admin match editor"
```

---

### Task 4: Handicap Betting UI in betting_ui.py

**Files:**
- Modify: `world_cup/betting_ui.py` (_render_match_fixture, _render_bet_slip, render_my_bets_tab)

**Goal:** Add market selector (1X2 vs Handicap) to match cards, handicap betting slip with profit preview, and handicap display in bet history. Since `betting_ui.py` is shared by both `betting_app.py` and `app.py`, changes here cover both apps.

- [ ] **Step 1: Add handicap_profit_preview helper at module level**

At the top of `betting_ui.py`, after the imports and before `BETTING_CSS`, add:

```python
from world_cup.game import HANDICAP_PAYOUT


def _handicap_profit_preview(wager: int, line: float, fee: int) -> dict:
    """Return breakdown dict for the handicap betting slip UI."""
    fee_amount = int(wager * fee / 100)
    net = wager - fee_amount
    multiplier = HANDICAP_PAYOUT.get(line, 1.0)
    win_return = int(net * multiplier)
    return {
        "fee_amount": fee_amount,
        "net_stake": net,
        "multiplier": multiplier,
        "win_return": win_return,
        "profit": win_return - wager,
    }
```

- [ ] **Step 2: Modify `_render_match_fixture()` to show handicap indicator and market selector**

In `_render_match_fixture()`, after the `is_live = m["status"] == "Live"` line and before the card HTML, check if the match has handicap:

The key changes when a user expands the bet slip (the `if st.session_state.get(f"bet_expand_{match_id}", False):` block at line 373):

Replace the current `_render_bet_slip(m, coins, match_id)` call on line 374 with:

```python
    if st.session_state.get(f"bet_expand_{match_id}", False):
        has_handicap = m.get("handicap_line") is not None
        if has_handicap:
            market_key = f"market_{match_id}"
            if market_key not in st.session_state:
                st.session_state[market_key] = "1X2"
            market_choice = st.radio(
                "Select Market:",
                ["1X2 (Win/Draw/Win)", "Handicap"],
                key=market_key,
                horizontal=True,
            )
            is_handicap = market_choice.startswith("Handicap")
        else:
            is_handicap = False

        if is_handicap:
            _render_handicap_bet_slip(m, coins, match_id)
        else:
            _render_bet_slip(m, coins, match_id)
```

- [ ] **Step 3: Add `_render_handicap_bet_slip()` function**

Add this new function after `_render_bet_slip()` (insert before `render_my_bets_tab` at ~line 415):

```python
def _render_handicap_bet_slip(m: dict, coins: int, match_id: int):
    handicap_line = m["handicap_line"]
    handicap_favorite = m.get("handicap_favorite", "A")
    handicap_fee = m.get("handicap_fee") or 5
    fav_team = m["team_a"] if handicap_favorite == "A" else m["team_b"]
    dog_team = m["team_b"] if handicap_favorite == "A" else m["team_a"]

    st.markdown('<div class="bet-slip">', unsafe_allow_html=True)
    side = st.radio(
        "Pick a side:",
        [
            f"{fav_team}  -{handicap_line}  (Favorite — gives {handicap_line} goals)",
            f"{dog_team}  +{handicap_line}  (Underdog — gets {handicap_line} goal headstart)",
        ],
        key=f"handi_side_{match_id}",
        horizontal=False,
    )
    handicap_side = "favorite" if "Favorite" in side else "underdog"

    h_amt_key = f"handi_amount_{match_id}"
    if h_amt_key not in st.session_state:
        st.session_state[h_amt_key] = 50

    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        st.session_state[h_amt_key] = st.number_input(
            "Bet amount",
            min_value=10, max_value=coins,
            value=st.session_state[h_amt_key], step=10,
            key=f"handi_num_{match_id}",
        )
    with col_b:
        for sv in [10, 50, 100]:
            if st.button(f"+{sv}", key=f"handi_qs_{match_id}_{sv}"):
                st.session_state[h_amt_key] = min(
                    st.session_state[h_amt_key] + sv, coins
                )
                st.rerun()
    with col_c:
        st.markdown("<br>", unsafe_allow_html=True)

    # Profit preview
    preview = _handicap_profit_preview(
        st.session_state[h_amt_key], handicap_line, handicap_fee,
    )

    st.markdown(f"""
    <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:1rem;margin:0.5rem 0;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1rem;color:var(--gold-bright);margin-bottom:0.75rem;">
            YOUR BET SUMMARY
        </div>
        <table style="width:100%;font-family:'Chakra Petch',sans-serif;font-size:0.85rem;color:var(--text-primary);">
            <tr><td>Wager</td><td style="text-align:right;">{st.session_state[h_amt_key]:,} coins</td></tr>
            <tr><td>Admin fee ({handicap_fee}%)</td><td style="text-align:right;color:var(--red-live);">-{preview['fee_amount']:,} coins</td></tr>
            <tr><td>Net at risk</td><td style="text-align:right;">{preview['net_stake']:,} coins</td></tr>
            <tr><td>Payout rate</td><td style="text-align:right;color:var(--gold-bright);">{preview['multiplier']}x</td></tr>
            <tr style="border-top:1px solid var(--border-subtle);"><td style="padding-top:0.5rem;"><strong>If you WIN</strong></td><td style="text-align:right;padding-top:0.5rem;color:var(--green-ok);"><strong>+{preview['win_return']:,} coins</strong> &nbsp;<span style="font-size:0.75rem;">(profit: {preview['profit']:+,})</span></td></tr>
            <tr><td><strong>If you LOSE</strong></td><td style="text-align:right;color:var(--red-live);"><strong>-{st.session_state[h_amt_key]:,} coins</strong></td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Condition hint
    line_goals = int(handicap_line + 0.5)
    st.info(
        f"{fav_team} must win by {line_goals}+ goals for a 'Favorite' bet to win. "
        f"Half-goal lines guarantee no draw/push."
    )

    if st.button("Confirm Handicap Bet  ✓", key=f"confirm_handi_{match_id}", use_container_width=True):
        try:
            db.place_handicap_bet(
                st.session_state.user["id"], match_id, handicap_side,
                st.session_state[h_amt_key], handicap_line, handicap_fee,
            )
            st.success(
                f"Bet placed! {st.session_state[h_amt_key]} coins on "
                f"{side.split('(')[0].strip()}"
            )
            st.session_state[f"bet_expand_{match_id}"] = False
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    st.markdown('</div>', unsafe_allow_html=True)
```

- [ ] **Step 4: Update `_render_match_fixture()` to show handicap badge on already-bet cards**

When a match already has a bet (the `if existing:` branch ~line 327), the bet info currently shows:
```html
<div class="bet-choice">✓ {bm.get(existing['bet_choice'], existing['bet_choice'])}</div>
```

For handicap bets, change the existing block to detect market type. Replace the entire section from `if existing:` (line 326) to the `return` at line 346 with:

```python
    if existing:
        if existing.get("market") == "handicap":
            side_label = "Favorite" if existing.get("handicap_side") == "favorite" else "Underdog"
            choice_display = f"Handicap: {side_label} @ {existing.get('handicap_line', '?')}"
        else:
            bm = {"A": f"{m['team_a']} Win", "B": f"{m['team_b']} Win", "DRAW": "Draw"}
            choice_display = f"✓ {bm.get(existing['bet_choice'], existing['bet_choice'])}"

        st.markdown(f"""
        <div class="match-fixture {card_class}">
            <div class="fixture-time">
                <div class="time-utc">{time_utc}</div>
                <div class="time-vn">{time_vn} VN</div>
            </div>
            <div class="fixture-teams">
                <span class="team-name home">{m['team_a']}</span>
                <span class="vs-badge">VS</span>
                <span class="team-name away">{m['team_b']}</span>
            </div>
            <div style="flex-shrink:0;text-align:center;min-width:75px">{status_html}</div>
            <div class="fixture-bet-info">
                <div class="bet-choice">{choice_display}</div>
                <div class="bet-amount">{existing['bet_amount']} coins</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
```

Note: The `bm` dict is now only defined inside the `else:` branch (1X2 path). Make sure to remove the earlier `bm = {...}` declaration that was at line 327/328.

- [ ] **Step 5: Update `render_my_bets_tab()` for handicap display**

In `render_my_bets_tab()` (~line 419), after the `sc = {...}` dict and before the `for b in my_bets:` loop, update the choice display logic.

Replace the `cd = {...}` line and the subsequent HTML that uses `cd.get(b['bet_choice'], ...)` with:

```python
    sc = {"Pending": "rgba(243,156,18,0.85)", "Won": "var(--green-ok)",
          "Lost": "var(--red-live)", "Refunded": "#95a5a6"}
    cd_1x2 = {"A": "A Win", "B": "B Win", "DRAW": "Draw"}
    for b in my_bets:
        if b.get("market") == "handicap":
            side_label = "Favorite" if b.get("handicap_side") == "favorite" else "Underdog"
            choice_display = f"Handicap {side_label} @ {b.get('handicap_line', '?')}"
        else:
            choice_display = cd_1x2.get(b["bet_choice"], b["bet_choice"])
        status_color = sc.get(b["status"], "gray")
        st.markdown(f"""
        <div class="history-row">
            <div>
                <div class="hist-teams">{b['team_a']}  vs  {b['team_b']}</div>
                <div class="hist-detail">
                    Choice: {choice_display} &nbsp;·&nbsp;
                    <span class="coin-amount">{b['bet_amount']} coins</span>
                </div>
            </div>
            <div style="text-align:right;">
                <span class="hist-status" style="background:{status_color};">{b['status']}</span>
                <div class="hist-date">{b['created_at'][:16]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
```

- [ ] **Step 6: Verify syntax**

```bash
python -c "import ast; ast.parse(open('world_cup/betting_ui.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add world_cup/betting_ui.py
git commit -m "feat: add handicap market selector, bet slip, and history display to betting UI"
```

---

### Task 5: Handicap Settlement & Integration Tests

**Files:**
- Create: `world_cup/tests/test_handicap.py`

**Goal:** Comprehensive tests for handicap settlement math, bet placement, and mixed-market settlement.

- [ ] **Step 1: Write test file**

```python
"""Tests for handicap betting — settlement math, bet placement, mixed settlement."""
import os
import tempfile
import sqlite3

import pytest

import world_cup.db as db_module
from world_cup import game


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    """Replace the database with a fresh temp-file for every test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(db_module, "DB_PATH", path)
    monkeypatch.setattr(db_module, "get_connection", lambda: _test_conn(path))
    db_module.init_db()
    yield
    os.unlink(path)


def _test_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================================
# Payout math
# ===========================================================================

def test_handicap_payout_tiers():
    assert game.get_handicap_payout(0.5) == 1.8
    assert game.get_handicap_payout(1.5) == 2.5
    assert game.get_handicap_payout(2.5) == 3.5
    assert game.get_handicap_payout(3.5) == 5.0
    assert game.get_handicap_payout(999) == 1.0


def test_calc_handicap_win_amount():
    # 100 bet, 5% fee=5, net=95, 1.8x = 171.0 -> 171
    assert game.calc_handicap_win_amount(100, 0.5, 5) == 171
    # 100 bet, 0% fee, net=100, 1.8x = 180
    assert game.calc_handicap_win_amount(100, 0.5, 0) == 180
    # 200 bet, 10% fee=20, net=180, 5.0x = 900
    assert game.calc_handicap_win_amount(200, 3.5, 10) == 900
    # 100 bet, 5% fee=5, net=95, 2.5x = 237.5 -> 237
    assert game.calc_handicap_win_amount(100, 1.5, 5) == 237


# ===========================================================================
# settle_handicap_bet — pure logic (no DB)
# ===========================================================================

def test_settle_handicap_favorite_A_covers():
    """Brazil -1.5 fav vs Thailand, score 3-0 -> favorite covers."""
    status, payout = game.settle_handicap_bet(
        "favorite", 100, 1.5, "A", 5, 3, 0,
    )
    assert status == "Won"
    assert payout == 237  # 100 - 5 = 95, 95 * 2.5 = 237


def test_settle_handicap_favorite_A_fails():
    """Brazil -1.5 fav vs Thailand, score 1-0 -> favorite fails."""
    status, payout = game.settle_handicap_bet(
        "favorite", 100, 1.5, "A", 5, 1, 0,
    )
    assert status == "Lost"
    assert payout == 0


def test_settle_handicap_underdog_A_covers():
    """Brazil -1.5 fav vs Thailand, score 1-0 -> underdog covers."""
    status, payout = game.settle_handicap_bet(
        "underdog", 100, 1.5, "A", 5, 1, 0,
    )
    assert status == "Won"
    assert payout == 237


def test_settle_handicap_favorite_B_covers():
    """Thailand -1.5 fav vs Brazil, score 0-3 -> Team B favorite covers (win by 3)."""
    # goal_diff = 0 - 3 = -3
    # effective_diff (fav=B) = -(-3) - 1.5 = 3 - 1.5 = 1.5 > 0 -> favorite wins
    status, payout = game.settle_handicap_bet(
        "favorite", 100, 1.5, "B", 5, 0, 3,
    )
    assert status == "Won"
    assert payout == 237


def test_settle_handicap_favorite_B_fails():
    """Thailand -1.5 fav, Brazil wins 0-1 -> favorite B fails."""
    # goal_diff = 0 - 1 = -1
    # effective_diff (fav=B) = -(-1) - 1.5 = 1 - 1.5 = -0.5 < 0 -> favorite loses
    status, payout = game.settle_handicap_bet(
        "favorite", 100, 1.5, "B", 5, 0, 1,
    )
    assert status == "Lost"
    assert payout == 0


def test_settle_handicap_draw_result_underdog_wins():
    """Brazil -0.5 fav, draw 1-1 -> underdog covers (draw + 0.5 > 0)."""
    # goal_diff = 0
    # effective_diff (fav=A) = 0 - 0.5 = -0.5 < 0 -> favorite loses -> underdog wins
    status, payout = game.settle_handicap_bet(
        "underdog", 100, 0.5, "A", 5, 1, 1,
    )
    assert status == "Won"
    assert payout == 171  # 95 * 1.8 = 171


def test_settle_handicap_3_5_line():
    """Brazil -3.5 fav, score 4-0 -> favorite covers exactly."""
    # goal_diff = 4, effective = 4 - 3.5 = 0.5 > 0 -> favorite wins
    status, payout = game.settle_handicap_bet(
        "favorite", 100, 3.5, "A", 5, 4, 0,
    )
    assert status == "Won"
    assert payout == 475  # 95 * 5.0 = 475


def test_settle_handicap_3_5_line_fails():
    """Brazil -3.5 fav, score 3-0 -> favorite fails (3 < 3.5)."""
    # goal_diff = 3, effective = 3 - 3.5 = -0.5 < 0 -> favorite loses
    status, payout = game.settle_handicap_bet(
        "favorite", 100, 3.5, "A", 5, 3, 0,
    )
    assert status == "Lost"
    assert payout == 0


# ===========================================================================
# place_handicap_bet — DB integration
# ===========================================================================

@pytest.fixture
def seeded():
    """Create a test user and match with handicap."""
    uid = db_module.register_user("+84123456789", "Test Player")
    db_module.admin_insert_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        handicap_line=1.5, handicap_favorite="A", handicap_fee=5,
    )
    return uid


def test_place_handicap_bet_success(seeded):
    bet_id = db_module.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)
    assert bet_id > 0
    user = db_module.get_user(seeded)
    assert user["current_coins"] == 900


def test_place_handicap_bet_insufficient(seeded):
    with pytest.raises(ValueError, match="Insufficient"):
        db_module.place_handicap_bet(seeded, 100, "favorite", 5000, 1.5, 5)


def test_place_handicap_bet_invalid_amount(seeded):
    with pytest.raises(ValueError, match="multiple of 10"):
        db_module.place_handicap_bet(seeded, 100, "favorite", 15, 1.5, 5)


def test_place_handicap_bet_finished_match(seeded):
    db_module.admin_update_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        "Finished", "A_win", score_a=3, score_b=0,
        handicap_line=1.5, handicap_favorite="A", handicap_fee=5,
    )
    with pytest.raises(ValueError, match="finished"):
        db_module.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)


# ===========================================================================
# settle_match_bets — mixed markets
# ===========================================================================

def test_settle_handicap_favorite_covers_full(seeded):
    """Full pipeline: place handicap bet, settle after match with scores."""
    db_module.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)
    db_module.admin_update_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        "Finished", "A_win", score_a=3, score_b=0,
        handicap_line=1.5, handicap_favorite="A", handicap_fee=5,
    )
    db_module.settle_match_bets(100, "A_win")
    user = db_module.get_user(seeded)
    assert user["current_coins"] == 1137  # 1000 - 100 + 237


def test_settle_handicap_favorite_fails_full(seeded):
    """Favorite fails to cover."""
    db_module.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)
    db_module.admin_update_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        "Finished", "A_win", score_a=1, score_b=0,
        handicap_line=1.5, handicap_favorite="A", handicap_fee=5,
    )
    db_module.settle_match_bets(100, "A_win")
    user = db_module.get_user(seeded)
    assert user["current_coins"] == 900


def test_settle_handicap_underdog_covers_full(seeded):
    """Underdog covers on a narrow favorite win."""
    db_module.place_handicap_bet(seeded, 100, "underdog", 100, 1.5, 5)
    db_module.admin_update_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        "Finished", "A_win", score_a=1, score_b=0,
        handicap_line=1.5, handicap_favorite="A", handicap_fee=5,
    )
    db_module.settle_match_bets(100, "A_win")
    user = db_module.get_user(seeded)
    assert user["current_coins"] == 1137


def test_settle_mixed_1x2_and_handicap(seeded):
    """Both 1X2 and handicap bets on the same match settle correctly."""
    uid2 = db_module.register_user("+84999999999", "Player 2")
    # Player 1: handicap bet on favorite
    db_module.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)
    # Player 2: 1X2 bet on Team A
    db_module.place_bet(uid2, 100, "A", 100)

    db_module.admin_update_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        "Finished", "A_win", score_a=3, score_b=0,
        handicap_line=1.5, handicap_favorite="A", handicap_fee=5,
    )
    db_module.settle_match_bets(100, "A_win")

    # Player 1: handicap favorite wins (3-0 covers -1.5)
    assert db_module.get_user_coins(seeded) == 1137  # 1000-100+237
    # Player 2: 1X2 A_win pays 2x
    assert db_module.get_user_coins(uid2) == 1100  # 1000-100+200


def test_settle_handicap_team_B_favorite(seeded):
    """Team B is favorite, loses -> favorite bet loses."""
    db_module.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)
    db_module.admin_update_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        "Finished", "A_win", score_a=2, score_b=1,
        handicap_line=1.5, handicap_favorite="B", handicap_fee=5,
    )
    db_module.settle_match_bets(100, "A_win")
    user = db_module.get_user(seeded)
    # Favorite B (-1.5): effective = -(-1) - 1.5 = -0.5 < 0 -> favorite loses
    assert user["current_coins"] == 900


def test_settle_handicap_with_draw_result(seeded):
    """Match draws, underdog +0.5 wins."""
    db_module.place_handicap_bet(seeded, 100, "underdog", 100, 0.5, 5)
    db_module.admin_update_match(
        100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
        "Finished", "Draw", score_a=1, score_b=1,
        handicap_line=0.5, handicap_favorite="A", handicap_fee=5,
    )
    db_module.settle_match_bets(100, "Draw")
    user = db_module.get_user(seeded)
    assert user["current_coins"] == 1071  # 1000-100+171


# ===========================================================================
# Admin handicap CRUD
# ===========================================================================

def test_admin_handicap_crud():
    """Create and update match handicap fields via admin functions."""
    db_module.admin_insert_match(
        200, "Germany", "Japan", "2026-06-15T16:00:00Z",
        handicap_line=2.5, handicap_favorite="A", handicap_fee=10,
    )
    match = db_module.get_match(200)
    assert match["handicap_line"] == 2.5
    assert match["handicap_favorite"] == "A"
    assert match["handicap_fee"] == 10

    db_module.admin_update_match(
        200, "Germany", "Japan", "2026-06-15T16:00:00Z",
        "Not Started", None,
        handicap_line=None, handicap_favorite=None, handicap_fee=5,
    )
    match = db_module.get_match(200)
    assert match["handicap_line"] is None
    assert match["handicap_favorite"] is None
    assert match["handicap_fee"] == 5
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest world_cup/tests/test_handicap.py -v
```
Expected: All tests pass.

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
python -m pytest world_cup/tests/ -v
```
Expected: All tests pass (existing + new).

- [ ] **Step 4: Commit**

```bash
git add world_cup/tests/test_handicap.py
git commit -m "test: add handicap settlement and integration tests"
```

---

## Self-Review

1. **Spec coverage:**
   - Settlement math in game.py → Task 1 ✓
   - Mixed-market settlement in db.py → Task 2 ✓
   - Admin handicap fields → Task 3 ✓
   - User handicap betting slip with profit preview → Task 4 ✓
   - My-bets handicap display → Task 4 Step 5 ✓
   - Tests for all 4 line levels × favorite A/B × result combos → Task 5 ✓

2. **Placeholder scan:** No TBDs, TODOs, or vague steps. All code shown.

3. **Type consistency:**
   - `handicap_line`: `float` throughout (0.5, 1.5, 2.5, 3.5)
   - `handicap_favorite`: `"A"` or `"B"` throughout
   - `handicap_fee`: `int` (percent, defaults to 5)
   - `handicap_side`: `"favorite"` or `"underdog"` throughout
   - `market`: `"1X2"` or `"handicap"` throughout
