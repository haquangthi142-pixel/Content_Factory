# Handicap Betting System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add handicap (spread) betting market alongside existing 1X2 market, with admin-configurable lines, tiered payouts, and transparent fee display.

**Architecture:** Three new columns on `matches` (handicap_line, handicap_favorite, handicap_fee) plus `score_a`/`score_b` for goal storage. Three new columns on `bets` (market, handicap_line, handicap_side). New `place_handicap_bet()` function separate from existing `place_bet()`. Settlement logic extended in `settle_match_bets()` to handle both markets. Admin match editor extended. UI shows market selector + profit preview in both apps.

**Tech Stack:** Python 3.11, Streamlit, SQLite (via sqlite3), football-data.org v4 API

---

### Task 1: DB Schema Migration — Add Columns

**Files:**
- Modify: `world_cup/db.py` (init_db function, ~line 17-69)

- [ ] **Step 1: Add score and handicap columns to init_db()**

Open `world_cup/db.py`. Find the `init_db()` function. After the existing `CREATE INDEX` statements (after line 66), add ALTER TABLE migrations inside a try/except block:

```python
        # -- Schema migrations (safe to run repeatedly) --
        for col, ddl in [
            ("score_a", "ALTER TABLE matches ADD COLUMN score_a INTEGER"),
            ("score_b", "ALTER TABLE matches ADD COLUMN score_b INTEGER"),
            ("handicap_line", "ALTER TABLE matches ADD COLUMN handicap_line REAL"),
            ("handicap_favorite", "ALTER TABLE matches ADD COLUMN handicap_favorite TEXT"),
            ("handicap_fee", "ALTER TABLE matches ADD COLUMN handicap_fee INTEGER DEFAULT 5"),
            ("market", "ALTER TABLE bets ADD COLUMN market TEXT DEFAULT '1X2'"),
            ("handicap_line_bet", "ALTER TABLE bets ADD COLUMN handicap_line REAL"),
            ("handicap_side", "ALTER TABLE bets ADD COLUMN handicap_side TEXT"),
        ]:
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass  # column already exists
```

- [ ] **Step 2: Verify migration**

Run:
```bash
python -c "from world_cup import db; db.init_db(); conn=db.get_connection(); cols=conn.execute(\"PRAGMA table_info(matches)\").fetchall(); print([c[1] for c in cols]); conn.close()"
```
Expected: `score_a`, `score_b`, `handicap_line`, `handicap_favorite`, `handicap_fee` appear in column list.

- [ ] **Step 3: Commit**

```bash
git add world_cup/db.py
git commit -m "feat: add score and handicap columns to db schema"
```

---

### Task 2: Store Scores During Match Sync

**Files:**
- Modify: `world_cup/db.py` (sync_matches_from_api, ~line 145-196)
- Modify: `world_cup/db.py` (upsert_match, ~line 204-219)
- Modify: `world_cup/db.py` (admin_update_match, ~line 488-498)
- Modify: `world_cup/db.py` (admin_insert_match, ~line 511-521)

- [ ] **Step 1: Update sync_matches_from_api to store scores**

In `sync_matches_from_api()`, change the section that parses scores. Currently:
```python
            result = None
            if status_raw in ("FINISHED", "AWARDED"):
                score = m.get("score", {}).get("fullTime", {})
                home = score.get("home")
                away = score.get("away")
                if home is not None and away is not None:
                    if home > away:
                        result = "A_win"
                    elif away > home:
                        result = "B_win"
                    else:
                        result = "Draw"
```

Replace with:
```python
            result = None
            score_a = None
            score_b = None
            if status_raw in ("FINISHED", "AWARDED"):
                score = m.get("score", {}).get("fullTime", {})
                home = score.get("home")
                away = score.get("away")
                if home is not None and away is not None:
                    score_a = home
                    score_b = away
                    if home > away:
                        result = "A_win"
                    elif away > home:
                        result = "B_win"
                    else:
                        result = "Draw"
```

And update the INSERT/UPSERT statement to include score_a, score_b:

```python
            conn.execute("""
                INSERT INTO matches (match_id, team_a, team_b, match_time, status, result, score_a, score_b)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    team_a    = excluded.team_a,
                    team_b    = excluded.team_b,
                    match_time = excluded.match_time,
                    status    = excluded.status,
                    result    = excluded.result,
                    score_a   = excluded.score_a,
                    score_b   = excluded.score_b
            """, (match_id, team_a, team_b, match_time, status, result, score_a, score_b))
```

- [ ] **Step 2: Update upsert_match signature**

Change `upsert_match()` function signature and body to include `score_a` and `score_b`:

```python
def upsert_match(match_id: int, team_a: str, team_b: str, match_time: str,
                 status: str = "Not Started", result: str = None,
                 score_a: int | None = None, score_b: int | None = None):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO matches (match_id, team_a, team_b, match_time, status, result, score_a, score_b)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                team_a    = excluded.team_a,
                team_b    = excluded.team_b,
                match_time = excluded.match_time,
                status    = excluded.status,
                result    = excluded.result,
                score_a   = excluded.score_a,
                score_b   = excluded.score_b
        """, (match_id, team_a, team_b, match_time, status, result, score_a, score_b))
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 3: Update admin_update_match**

Change `admin_update_match()` signature and body:

```python
def admin_update_match(match_id: int, team_a: str, team_b: str, match_time: str,
                       status: str, result: str | None,
                       score_a: int | None = None, score_b: int | None = None,
                       handicap_line: float | None = None,
                       handicap_favorite: str | None = None,
                       handicap_fee: int | None = None):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE matches SET team_a = ?, team_b = ?, match_time = ?,
               status = ?, result = ?, score_a = ?, score_b = ?,
               handicap_line = ?, handicap_favorite = ?, handicap_fee = ?
               WHERE match_id = ?""",
            (team_a, team_b, match_time, status, result, score_a, score_b,
             handicap_line, handicap_favorite, handicap_fee, match_id),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Update admin_insert_match**

Change `admin_insert_match()` signature and body:

```python
def admin_insert_match(match_id: int, team_a: str, team_b: str, match_time: str,
                       status: str = "Not Started", result: str | None = None,
                       score_a: int | None = None, score_b: int | None = None,
                       handicap_line: float | None = None,
                       handicap_favorite: str | None = None,
                       handicap_fee: int | None = None):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO matches (match_id, team_a, team_b, match_time, status, result,
               score_a, score_b, handicap_line, handicap_favorite, handicap_fee)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (match_id, team_a, team_b, match_time, status, result,
             score_a, score_b, handicap_line, handicap_favorite, handicap_fee),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 5: Commit**

```bash
git add world_cup/db.py
git commit -m "feat: store scores in matches and update admin CRUD for handicap fields"
```

---

### Task 3: Handicap Payout Helper + Place Handicap Bet

**Files:**
- Modify: `world_cup/db.py` (new functions, add after place_bet ~line 304)

- [ ] **Step 1: Add payout helper and place_handicap_bet function**

Add these two functions after `place_bet()` (after line 304):

```python
HANDICAP_PAYOUT = {0.5: 1.8, 1.5: 2.5, 2.5: 3.5, 3.5: 5.0}


def get_handicap_payout(line: float) -> float:
    return HANDICAP_PAYOUT.get(line, 1.0)


def calc_handicap_win_amount(bet_amount: int, handicap_line: float, fee_percent: int) -> int:
    """Calculate payout for a winning handicap bet. Fee is deducted from stake first."""
    fee = int(bet_amount * fee_percent / 100)
    net_stake = bet_amount - fee
    multiplier = get_handicap_payout(handicap_line)
    return int(net_stake * multiplier)


def place_handicap_bet(user_id: int, match_id: int, handicap_side: str,
                       bet_amount: int, handicap_line: float,
                       handicap_fee: int) -> int:
    conn = get_connection()
    try:
        if bet_amount <= 0 or bet_amount % 10 != 0:
            raise ValueError("Bet amount must be a positive multiple of 10")

        coins = conn.execute(
            "SELECT current_coins FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not coins:
            raise ValueError("User not found")
        if coins["current_coins"] < bet_amount:
            raise ValueError(f"Insufficient coins. You have {coins['current_coins']}.")

        match = conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        if not match:
            raise ValueError("Match not found")
        if match["status"] == "Finished":
            raise ValueError("Cannot bet on a finished match")

        conn.execute(
            "UPDATE users SET current_coins = current_coins - ? WHERE id = ?",
            (bet_amount, user_id),
        )
        cur = conn.execute(
            """INSERT INTO bets (user_id, match_id, bet_choice, bet_amount, market,
               handicap_line, handicap_side)
               VALUES (?, ?, ?, ?, 'handicap', ?, ?)""",
            (user_id, match_id, handicap_side, bet_amount, handicap_line, handicap_side),
        )
        bet_id = cur.lastrowid
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, -?, 'bet', ?)",
            (user_id, bet_amount,
             f"Handicap bet on match #{match_id}: {handicap_side} @ {handicap_line}"),
        )
        conn.commit()
        return bet_id
    finally:
        conn.close()
```

- [ ] **Step 2: Verify the functions import correctly**

```bash
python -c "from world_cup import db; print(db.get_handicap_payout(1.5)); print(db.calc_handicap_win_amount(100, 1.5, 5))"
```
Expected output:
```
2.5
237
```

- [ ] **Step 3: Commit**

```bash
git add world_cup/db.py
git commit -m "feat: add handicap bet placement and payout helpers to db layer"
```

---

### Task 4: Handicap Settlement Logic

**Files:**
- Modify: `world_cup/db.py` (settle_match_bets, ~line 307-346)

- [ ] **Step 1: Rewrite settle_match_bets to handle both markets**

Replace the existing `settle_match_bets()` function:

```python
def settle_match_bets(match_id: int, result: str):
    """Settle all pending bets for a match. Handles both 1X2 and handicap markets."""
    conn = get_connection()
    try:
        match = conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        if not match:
            conn.close()
            return

        score_a = match["score_a"]
        score_b = match["score_b"]

        conn.execute(
            "UPDATE matches SET result = ?, status = 'Finished' WHERE match_id = ?",
            (result, match_id),
        )
        pending = conn.execute(
            "SELECT * FROM bets WHERE match_id = ? AND status = 'Pending'", (match_id,)
        ).fetchall()

        for bet in pending:
            if bet.get("market") == "handicap":
                _settle_handicap_bet(conn, bet, match)
            else:
                _settle_1x2_bet(conn, bet, result)

        conn.commit()
    finally:
        conn.close()


def _settle_1x2_bet(conn, bet, result: str):
    won = (
        (bet["bet_choice"] == "A" and result == "A_win") or
        (bet["bet_choice"] == "B" and result == "B_win") or
        (bet["bet_choice"] == "DRAW" and result == "Draw")
    )
    if won:
        payout = bet["bet_amount"] * 2
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


def _settle_handicap_bet(conn, bet, match):
    score_a = match["score_a"]
    score_b = match["score_b"]

    if score_a is None or score_b is None:
        return  # can't settle without scores

    handicap_line = bet["handicap_line"]
    handicap_favorite = match["handicap_favorite"]
    handicap_fee = match.get("handicap_fee") or 5

    goal_diff = score_a - score_b

    if handicap_favorite == "A":
        effective_diff = goal_diff - handicap_line
    else:
        effective_diff = -goal_diff - handicap_line

    if bet["handicap_side"] == "favorite":
        won = effective_diff > 0
    else:
        won = effective_diff < 0

    if won:
        payout = calc_handicap_win_amount(
            bet["bet_amount"], handicap_line, handicap_fee
        )
        conn.execute(
            "UPDATE bets SET status = 'Won', settled_at = datetime('now') WHERE bet_id = ?",
            (bet["bet_id"],),
        )
        conn.execute("UPDATE users SET current_coins = current_coins + ? WHERE id = ?",
                     (payout, bet["user_id"]))
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, 'win', ?)",
            (bet["user_id"], payout, f"Won handicap bet #{bet['bet_id']}"),
        )
    else:
        conn.execute(
            "UPDATE bets SET status = 'Lost', settled_at = datetime('now') WHERE bet_id = ?",
            (bet["bet_id"],),
        )
```

- [ ] **Step 2: Commit**

```bash
git add world_cup/db.py
git commit -m "feat: add handicap bet settlement logic"
```

---

### Task 5: Admin Match Editor — Handicap Fields

**Files:**
- Modify: `world_cup/admin.py` (_render_matches function, ~line 132-207)

- [ ] **Step 1: Add handicap fields to "Add Match" form**

In `_render_matches()`, in the "Add Match" form expander (after the `c3, c4 = st.columns(2)` block for status/result, before `st.form_submit_button`), add:

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

And update the `st.form_submit_button` handler to pass the new fields:

```python
            if st.form_submit_button("Add Match"):
                if team_a.strip() and team_b.strip() and match_time.strip():
                    db.admin_insert_match(
                        match_id, team_a, team_b, match_time, status,
                        None if result == "None" else result,
                        score_a=None, score_b=None,
                        handicap_line=None if handicap_line == "None" else float(handicap_line),
                        handicap_favorite=handicap_favorite if handicap_line != "None" else None,
                        handicap_fee=handicap_fee,
                    )
                    st.success(f"Added match #{match_id}")
                    st.rerun()
                else:
                    st.warning("Team A, Team B, and Match Time are required.")
```

- [ ] **Step 2: Add handicap fields to "Edit Match" section**

In the edit section (after the status/result selectboxes, before `col_save, col_del`), add score and handicap fields:

```python
        c5, c6 = st.columns(2)
        new_score_a = c5.number_input("Score A", value=match.get("score_a") or 0, key="edit_score_a")
        new_score_b = c6.number_input("Score B", value=match.get("score_b") or 0, key="edit_score_b")

        st.markdown("---")
        st.caption("Handicap Settings")
        hc1, hc2, hc3 = st.columns(3)
        line_opts = ["None", "0.5", "1.5", "2.5", "3.5"]
        cur_line = str(match.get("handicap_line") or "None")
        new_line = hc1.selectbox(
            "Handicap Line", line_opts,
            index=line_opts.index(cur_line) if cur_line in line_opts else 0,
            key="edit_handicap_line",
        )
        fav_opts = ["A", "B"]
        cur_fav = match.get("handicap_favorite") or "A"
        new_favorite = hc2.selectbox(
            "Favorite", fav_opts,
            index=fav_opts.index(cur_fav) if cur_fav in fav_opts else 0,
            key="edit_handicap_favorite",
        )
        new_fee = hc3.number_input(
            "Fee %", min_value=0, max_value=20,
            value=match.get("handicap_fee") or 5, step=1,
            key="edit_handicap_fee",
        )
```

And update the Save Changes button handler:

```python
        with col_save:
            if st.button("Save Changes", key="save_match"):
                db.admin_update_match(
                    selected_id, new_team_a, new_team_b, new_time, new_status,
                    None if new_result == "None" else new_result,
                    score_a=new_score_a, score_b=new_score_b,
                    handicap_line=None if new_line == "None" else float(new_line),
                    handicap_favorite=new_favorite if new_line != "None" else None,
                    handicap_fee=new_fee,
                )
                st.success("Match updated.")
                st.rerun()
```

- [ ] **Step 3: Commit**

```bash
git add world_cup/admin.py
git commit -m "feat: add handicap and score fields to admin match editor"
```

---

### Task 6: Handicap UI in betting_app.py — Betting Slip

**Files:**
- Modify: `world_cup/betting_app.py` (Tab 1 — Place Bets section, ~line 562-738)

- [ ] **Step 1: Add handicap info display to match cards that have it**

In the match card rendering (the `if existing:` and `else:` branches within the match loop), when a match has `handicap_line` set, show a handicap indicator. Add a helper function at the top of the file (after imports, before BETTING_CSS):

```python
HANDICAP_PAYOUT = {0.5: 1.8, 1.5: 2.5, 2.5: 3.5, 3.5: 5.0}
HANDICAP_LABEL = {
    0.5: "±0.5", 1.5: "±1.5", 2.5: "±2.5", 3.5: "±3.5",
}


def handicap_profit_preview(wager: int, line: float, fee: int) -> dict:
    """Return breakdown dict for the UI."""
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

- [ ] **Step 2: Modify the match card loop to add market selector**

Find the `else:` branch for matches without existing bets (around line 668). Currently it shows a card + "Place Bet" button with an expandable 1X2 slip. Modify it so that when a match has a handicap, it shows two betting options.

Replace the card+button section (from around line 668 to line 737) with the following. 

The key change: when `m["handicap_line"]` is not None, show a market selector (1X2 vs Handicap) above the betting slip. When Handicap is selected, render the handicap slip with profit preview.

In the existing `else:` branch (line 668), after the match fixture card markup, add the market selector before the expanded betting slip:

```python
                # Check if handicap market exists for this match
                has_handicap = m.get("handicap_line") is not None

                if existing is None and st.session_state.get(f"bet_expand_{match_id}", False):
                    st.markdown('<div class="bet-slip">', unsafe_allow_html=True)

                    if has_handicap:
                        market_choice = st.radio(
                            "Select Market:",
                            ["1X2 (Win/Draw/Win)", "Handicap"],
                            key=f"market_{match_id}",
                            horizontal=True,
                        )
                        is_handicap = market_choice.startswith("Handicap")
                    else:
                        is_handicap = False

                    if not is_handicap:
                        # --- Existing 1X2 slip (unchanged) ---
                        choice = st.radio(
                            "Pick outcome:",
                            [f"{m['team_a']} Win", "Draw", f"{m['team_b']} Win"],
                            key=f"choice_{match_id}",
                            horizontal=True,
                        )
                        choice_map = {
                            f"{m['team_a']} Win": "A",
                            "Draw": "DRAW",
                            f"{m['team_b']} Win": "B",
                        }
                        # ... rest of existing 1X2 slip code ...
                    else:
                        # --- Handicap slip ---
                        handicap_line = m["handicap_line"]
                        handicap_favorite = m.get("handicap_favorite", "A")
                        handicap_fee = m.get("handicap_fee") or 5
                        fav_team = m["team_a"] if handicap_favorite == "A" else m["team_b"]
                        dog_team = m["team_b"] if handicap_favorite == "A" else m["team_a"]

                        side = st.radio(
                            "Pick a side:",
                            [
                                f"{fav_team} -{handicap_line} (Favorite, gives {handicap_line} goals)",
                                f"{dog_team} +{handicap_line} (Underdog, gets {handicap_line} goal headstart)",
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
                                min_value=10, max_value=coins, value=st.session_state[h_amt_key],
                                step=10, key=f"handi_num_{match_id}",
                            )
                        with col_b:
                            for sv in [10, 50, 100]:
                                if st.button(f"+{sv}", key=f"handi_qs_{match_id}_{sv}"):
                                    st.session_state[h_amt_key] = min(st.session_state[h_amt_key] + sv, coins)
                                    st.rerun()

                        with col_c:
                            st.markdown("<br>", unsafe_allow_html=True)

                        # Profit preview
                        preview = handicap_profit_preview(
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
                                    user["id"], match_id, handicap_side,
                                    st.session_state[h_amt_key], handicap_line, handicap_fee,
                                )
                                st.success(f"Bet placed! {st.session_state[h_amt_key]} coins on {side.split('(')[0].strip()}")
                                st.session_state[f"bet_expand_{match_id}"] = False
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
```

Note: The existing 1X2 slip code (choice radio, amount input, confirm button) should still be used when `is_handicap` is False. Keep the existing code in the `if not is_handicap:` branch.

- [ ] **Step 2: Update My Bets tab to show handicap bet details**

In Tab 2 (My Bets, ~line 743-781), the history row already shows `bet_choice`. For handicap bets, `bet_choice` stores "favorite" or "underdog". The `cd` dict maps these, but for handicap bets the display needs adjustment.

After the `cd = {...}` line, add:

```python
                if b.get("market") == "handicap":
                    choice_display = f"{b.get('handicap_side', '?')} @ {b.get('handicap_line', '?')}"
                else:
                    choice_display = cd.get(b["bet_choice"], b["bet_choice"])
```

And use `choice_display` in the history row markup instead of `cd.get(b['bet_choice'], b['bet_choice'])`.

- [ ] **Step 3: Commit**

```bash
git add world_cup/betting_app.py
git commit -m "feat: add handicap betting UI to betting_app with profit preview"
```

---

### Task 7: Handicap UI in app.py — Integrated View

**Files:**
- Modify: `world_cup/app.py` (_render_betting_game function, Tab 1 — Place Bets, ~line 100-192)

- [ ] **Step 1: Apply same pattern from betting_app.py**

In `app.py`, the `_render_betting_game()` function has its own simpler betting UI in the "Place Bets" tab (lines 100-192). After the existing `cm = {...}` mapping (around line 164), add the handicap handling.

The key difference from betting_app.py: `app.py` has a simpler match layout (no CSS cards). The handicap slip follows the same pattern but with inline markdown instead of cards.

Replace the expanded betting section (around lines 154-191) to add market selector when the match has handicap set. The structure matches Task 6 — add market radio, handicap side radio, amount input with quick-add buttons, profit preview table, and confirm button.

Since `app.py` uses `db.get_connection()`/`conn.close()` to get match data, modify the fetch query in Tab 1 to include handicap columns:

Find the conn query (around line 115-119):
```python
        conn = db.get_connection()
        matches = conn.execute(
            "SELECT * FROM matches WHERE status != 'Finished' ORDER BY match_time LIMIT 50"
        ).fetchall()
        conn.close()
```

This already uses `SELECT *` so handicap columns will be included automatically.

Within the match loop (around line 154-191), add the same handicap slip pattern. Import `HANDICAP_PAYOUT` and `handicap_profit_preview` at the top of app.py:

```python
from world_cup.db import HANDICAP_PAYOUT
```

And add the helper function at module level in app.py:

```python
def _handicap_profit_preview(wager: int, line: float, fee: int) -> dict:
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

Then in the expanded bet section, after checking `st.session_state.get(f"bet_expand_{match_id}", False)`:

```python
                has_handicap = m.get("handicap_line") is not None

                if existing is None and st.session_state.get(f"bet_expand_{match_id}", False):
                    st.markdown("---")

                    if has_handicap:
                        market_choice = st.radio(
                            "Select Market:",
                            ["1X2 (Win/Draw/Win)", "Handicap"],
                            key=f"market_{match_id}",
                            horizontal=True,
                        )
                        is_handicap = market_choice.startswith("Handicap")
                    else:
                        is_handicap = False

                    if not is_handicap:
                        # existing 1X2 code...
                        pass
                    else:
                        # handicap slip — same pattern as betting_app.py
                        handicap_line = m["handicap_line"]
                        handicap_favorite = m.get("handicap_favorite", "A")
                        handicap_fee = m.get("handicap_fee") or 5
                        fav_team = m["team_a"] if handicap_favorite == "A" else m["team_b"]
                        dog_team = m["team_b"] if handicap_favorite == "A" else m["team_a"]

                        side = st.radio(
                            "Pick a side:",
                            [
                                f"{fav_team} -{handicap_line} (Favorite, gives {handicap_line} goals)",
                                f"{dog_team} +{handicap_line} (Underdog, gets {handicap_line} goal headstart)",
                            ],
                            key=f"handi_side_{match_id}",
                            horizontal=False,
                        )
                        handicap_side = "favorite" if "Favorite" in side else "underdog"

                        h_amt_key = f"handi_amount_{match_id}"
                        if h_amt_key not in st.session_state:
                            st.session_state[h_amt_key] = 50

                        ca, cb, cc = st.columns([1, 1, 1])
                        with ca:
                            st.session_state[h_amt_key] = st.number_input(
                                "Bet amount", min_value=10, max_value=coins,
                                value=st.session_state[h_amt_key], step=10,
                                key=f"handi_num_{match_id}",
                            )
                        with cb:
                            for sv in [10, 50, 100]:
                                if st.button(f"+{sv}", key=f"handi_qs_{match_id}_{sv}"):
                                    st.session_state[h_amt_key] = min(st.session_state[h_amt_key] + sv, coins)
                                    st.rerun()
                        with cc:
                            st.markdown("<br>", unsafe_allow_html=True)

                        preview = _handicap_profit_preview(
                            st.session_state[h_amt_key], handicap_line, handicap_fee,
                        )

                        st.markdown(f"""
                        <div style="background:var(--bg-card);border:1px solid var(--border-gold);border-radius:10px;padding:1rem;margin:0.5rem 0;">
                            <div style="font-family:Bebas Neue,sans-serif;font-size:1rem;color:var(--gold-bright);margin-bottom:0.75rem;">
                                YOUR BET SUMMARY
                            </div>
                            <table style="width:100%;font-family:Chakra Petch,sans-serif;font-size:0.85rem;color:var(--text-primary);">
                                <tr><td>Wager</td><td style="text-align:right;">{st.session_state[h_amt_key]:,} coins</td></tr>
                                <tr><td>Admin fee ({handicap_fee}%)</td><td style="text-align:right;color:var(--accent-danger);">-{preview['fee_amount']:,} coins</td></tr>
                                <tr><td>Net at risk</td><td style="text-align:right;">{preview['net_stake']:,} coins</td></tr>
                                <tr><td>Payout rate</td><td style="text-align:right;color:var(--gold-bright);">{preview['multiplier']}x</td></tr>
                                <tr style="border-top:1px solid var(--border-subtle);"><td style="padding-top:0.5rem;"><strong>If you WIN</strong></td><td style="text-align:right;padding-top:0.5rem;color:var(--accent-done);"><strong>+{preview['win_return']:,} coins</strong> &nbsp;<span style="font-size:0.75rem;">(profit: {preview['profit']:+,})</span></td></tr>
                                <tr><td><strong>If you LOSE</strong></td><td style="text-align:right;color:var(--accent-danger);"><strong>-{st.session_state[h_amt_key]:,} coins</strong></td></tr>
                            </table>
                        </div>
                        """, unsafe_allow_html=True)

                        line_goals = int(handicap_line + 0.5)
                        st.info(
                            f"{fav_team} must win by {line_goals}+ goals for a 'Favorite' bet to win. "
                            f"Half-goal lines guarantee no draw/push."
                        )

                        if st.button("Confirm Handicap Bet  ✓", key=f"confirm_handi_{match_id}", use_container_width=True):
                            try:
                                db.place_handicap_bet(
                                    user["id"], match_id, handicap_side,
                                    st.session_state[h_amt_key], handicap_line, handicap_fee,
                                )
                                st.success(f"Bet placed! {st.session_state[h_amt_key]} coins on {side.split('(')[0].strip()}")
                                st.session_state[f"bet_expand_{match_id}"] = False
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
```

- [ ] **Step 2: Update My Bets tab in app.py for handicap display**

In the My Bets tab (around line 193-224), add handicap detection similar to Task 6 Step 2:

After `cd = {...}` line, add:
```python
                if b.get("market") == "handicap":
                    choice_display = f"{b.get('handicap_side', '?')} @ {b.get('handicap_line', '?')}"
                else:
                    choice_display = cd.get(b["bet_choice"], b["bet_choice"])
```

And use `choice_display` in the history row HTML.

- [ ] **Step 3: Commit**

```bash
git add world_cup/app.py
git commit -m "feat: add handicap betting UI to app.py integrated view"
```

---

### Task 8: Tests

**Files:**
- Create: `world_cup/tests/test_handicap.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for handicap betting system."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from world_cup import db


@pytest.fixture(autouse=True)
def fresh_db():
    """Re-initialize DB in memory mode for each test, then clean up."""
    db.DB_PATH = ":memory:"
    db.init_db()
    yield
    db.DB_PATH = os.path.join(os.path.dirname(db.__file__), "game.db")


@pytest.fixture
def seeded(fresh_db):
    """Create a test user."""
    uid = db.register_user("+84123456789", "Test Player")
    return uid


def test_handicap_payout_tiers():
    assert db.get_handicap_payout(0.5) == 1.8
    assert db.get_handicap_payout(1.5) == 2.5
    assert db.get_handicap_payout(2.5) == 3.5
    assert db.get_handicap_payout(3.5) == 5.0
    assert db.get_handicap_payout(999) == 1.0  # unknown line


def test_calc_handicap_win_amount():
    # 100 bet, 5% fee=5, net=95, 2.5x = 237.5 -> 237
    assert db.calc_handicap_win_amount(100, 1.5, 5) == 237
    # 100 bet, 0% fee, net=100, 1.8x = 180
    assert db.calc_handicap_win_amount(100, 0.5, 0) == 180
    # 200 bet, 10% fee=20, net=180, 5.0x = 900
    assert db.calc_handicap_win_amount(200, 3.5, 10) == 900


def test_place_handicap_bet_success(seeded):
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    bet_id = db.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)
    assert bet_id > 0

    user = db.get_user(seeded)
    assert user["current_coins"] == 900  # 1000 - 100


def test_place_handicap_bet_insufficient(seeded):
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    with pytest.raises(ValueError, match="Insufficient"):
        db.place_handicap_bet(seeded, 100, "favorite", 5000, 1.5, 5)


def test_place_handicap_bet_invalid_amount(seeded):
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    with pytest.raises(ValueError, match="multiple of 10"):
        db.place_handicap_bet(seeded, 100, "favorite", 15, 1.5, 5)


def test_place_handicap_bet_finished_match(seeded):
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          status="Finished", result="A_win", score_a=3, score_b=0,
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    with pytest.raises(ValueError, match="finished"):
        db.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)


def test_settle_handicap_favorite_covers(seeded):
    """Brazil -1.5 favorite, wins 3-0 -> favorite covers."""
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          status="Live", handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)

    # Simulate finished match: 3-0
    db.admin_update_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          "Finished", "A_win", score_a=3, score_b=0,
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.settle_match_bets(100, "A_win")

    user = db.get_user(seeded)
    # Bet 100, win returns 237. Net = 1000 - 100 + 237 = 1137
    assert user["current_coins"] == 1137


def test_settle_handicap_favorite_fails(seeded):
    """Brazil -1.5 favorite, wins 1-0 -> favorite fails, underdog covers."""
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          status="Live", handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)

    db.admin_update_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          "Finished", "A_win", score_a=1, score_b=0,
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.settle_match_bets(100, "A_win")

    user = db.get_user(seeded)
    assert user["current_coins"] == 900  # lost the 100 bet


def test_settle_handicap_underdog_covers(seeded):
    """Thailand +1.5 underdog (Brazil -1.5 fav), Brazil wins 1-0 -> underdog covers."""
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          status="Live", handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.place_handicap_bet(seeded, 100, "underdog", 100, 1.5, 5)

    db.admin_update_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          "Finished", "A_win", score_a=1, score_b=0,
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.settle_match_bets(100, "A_win")

    user = db.get_user(seeded)
    assert user["current_coins"] == 1137  # underdog covers, wins


def test_settle_handicap_team_b_favorite(seeded):
    """Thailand is favorite (-1.5), Brazil +1.5 underdog. Brazil wins 1-0 -> underdog covers."""
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          status="Live", handicap_line=1.5, handicap_favorite="B", handicap_fee=5)
    db.place_handicap_bet(seeded, 100, "favorite", 100, 1.5, 5)

    db.admin_update_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          "Finished", "A_win", score_a=2, score_b=1,
                          handicap_line=1.5, handicap_favorite="B", handicap_fee=5)
    db.settle_match_bets(100, "A_win")

    user = db.get_user(seeded)
    # Favorite B (-1.5): -goal_diff - L = -(-1) - 1.5 = 1 - 1.5 = -0.5 < 0 -> favorite loses
    assert user["current_coins"] == 900  # lost


def test_settle_handicap_draw_result(seeded):
    """Brazil -0.5 favorite, match draws 1-1 -> underdog covers (draw + 0.5 > 0)."""
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          status="Live", handicap_line=0.5, handicap_favorite="A", handicap_fee=5)
    db.place_handicap_bet(seeded, 100, "underdog", 100, 0.5, 5)

    db.admin_update_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          "Finished", "Draw", score_a=1, score_b=1,
                          handicap_line=0.5, handicap_favorite="A", handicap_fee=5)
    db.settle_match_bets(100, "Draw")

    user = db.get_user(seeded)
    # Underdog +0.5: effective = 0 - 0.5 = -0.5 < 0 -> underdog wins
    # Bet 100, 5% fee=5, net=95, 1.8x = 171
    assert user["current_coins"] == 1071


def test_1x2_bets_still_work(seeded):
    """Existing 1X2 betting still settles correctly after handicap changes."""
    db.admin_insert_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          status="Live", handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.place_bet(seeded, 100, "A", 100)

    db.admin_update_match(100, "Brazil", "Thailand", "2026-06-14T20:00:00Z",
                          "Finished", "A_win", score_a=2, score_b=0,
                          handicap_line=1.5, handicap_favorite="A", handicap_fee=5)
    db.settle_match_bets(100, "A_win")

    user = db.get_user(seeded)
    assert user["current_coins"] == 1100  # 1000 - 100 + 200


def test_admin_handicap_crud(seeded):
    """Admin can create and update matches with handicap fields."""
    db.admin_insert_match(200, "Germany", "Japan", "2026-06-15T16:00:00Z",
                          handicap_line=2.5, handicap_favorite="A", handicap_fee=10)

    match = db.get_match(200)
    assert match["handicap_line"] == 2.5
    assert match["handicap_favorite"] == "A"
    assert match["handicap_fee"] == 10

    db.admin_update_match(200, "Germany", "Japan", "2026-06-15T16:00:00Z",
                          "Not Started", None, handicap_line=None, handicap_favorite=None, handicap_fee=5)

    match = db.get_match(200)
    assert match["handicap_line"] is None
    assert match["handicap_favorite"] is None
    assert match["handicap_fee"] == 5
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest world_cup/tests/test_handicap.py -v
```

All tests should pass.

- [ ] **Step 3: Commit**

```bash
git add world_cup/tests/test_handicap.py
git commit -m "test: add handicap betting unit tests"
```

---

## Self-Review Checklist

1. **Spec coverage:** Each spec section maps to a task — DB changes (Tasks 1-4), admin UI (Task 5), user UI in both apps (Tasks 6-7), tests (Task 8).
2. **Placeholder scan:** No TBDs, TODOs, or vague "add error handling" steps. All code is shown.
3. **Type consistency:** `handicap_line` is `float` throughout. `handicap_fee` defaults to 5 everywhere. `handicap_favorite` is `'A'` or `'B'`.
