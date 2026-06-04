# Multi-Bet Per Match — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the 1-bet-per-match restriction. Users can place unlimited bets on a single match across both 1X2 and Handicap markets.

**Architecture:** Single file change in `betting_ui.py`. Replace `fetchone()` with `fetchall()`, remove early-return lock on existing bets, add a compact existing-bets list, and always show the market selector when handicap is available. No DB changes — the schema already supports multiple bets per (user, match).

**Tech Stack:** Python 3.11, Streamlit, SQLite

**Prerequisite:** This plan assumes the handicap UI from `2026-06-04-handicap-betting-remaining.md` Task 4 is also implemented. The market selector code here integrates with `_render_handicap_bet_slip()` defined there. If handicap UI is not yet done, the `has_handicap` checks gracefully degrade (no handicap features shown).

---

### Task 1: Remove 1-Bet Lock in betting_ui.py

**Files:**
- Modify: `world_cup/betting_ui.py` — `_render_match_fixture()` (lines 305-374) and `_render_bet_slip()` (lines 377-412)

**Goal:** `_render_match_fixture` currently calls `fetchone()`, and if a bet exists, renders a locked card and `return`s early. Replace with `fetchall()`, show existing bets as a compact list, and always expose the betting slip. Also add market selector to the bet slip when handicap exists.

- [ ] **Step 1: Replace `_render_match_fixture()` — remove early return, add existing bets list**

Replace the entire function from line 305 to line 374 with:

```python
def _render_match_fixture(m: dict, utc_dt: datetime, user_id: int, coins: int):
    match_id = m["match_id"]
    vn_dt = utc_dt.astimezone(VN_TZ)
    time_utc = utc_dt.strftime("%H:%M")
    time_vn = vn_dt.strftime("%H:%M")

    conn = db.get_connection()
    existing_bets = conn.execute(
        "SELECT * FROM bets WHERE user_id = ? AND match_id = ? ORDER BY created_at",
        (user_id, match_id),
    ).fetchall()
    conn.close()

    is_live = m["status"] == "Live"
    has_bets = len(existing_bets) > 0
    card_class = "live" if is_live else ("already-bet" if has_bets else "")

    if is_live:
        status_html = '<span class="status-badge live-badge">● LIVE</span>'
    else:
        status_html = '<span class="status-badge upcoming-badge">📅 Upcoming</span>'

    # Match card
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
    """, unsafe_allow_html=True)

    # If user has existing bets, show them as a compact list
    if has_bets:
        _render_existing_bets(existing_bets, m)

    # Close the match-fixture div
    st.markdown("</div>", unsafe_allow_html=True)

    # "Place Bet" / "Place Another Bet" button — always visible
    btn_col1, btn_col2 = st.columns([5, 1])
    with btn_col2:
        ek = f"bet_expand_{match_id}"
        if ek not in st.session_state:
            st.session_state[ek] = False
        btn_label = "Place Another Bet  →" if has_bets else "Place Bet  →"
        if st.button(btn_label, key=f"btn_{match_id}", use_container_width=True):
            st.session_state[ek] = not st.session_state[ek]
            st.rerun()

    # Expanded bet slip
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

- [ ] **Step 2: Add `_render_existing_bets()` helper**

Insert this new function before `_render_match_fixture()` (before line 305):

```python
def _render_existing_bets(bets: list, m: dict):
    """Render a compact list of the user's existing bets on this match."""
    sc = {"Pending": "rgba(243,156,18,0.85)", "Won": "#2ecc71",
          "Lost": "#e74c3c", "Refunded": "#95a5a6"}

    rows = []
    for b in bets:
        if b.get("market") == "handicap":
            side = "Favorite" if b.get("handicap_side") == "favorite" else "Underdog"
            choice = f"Handicap · {side} @ {b.get('handicap_line', '?')}"
        else:
            cd = {"A": f"{m['team_a']} Win", "B": f"{m['team_b']} Win", "DRAW": "Draw"}
            choice = f"1X2 · {cd.get(b['bet_choice'], b['bet_choice'])}"

        s_color = sc.get(b["status"], "gray")
        rows.append(
            f"<tr><td style='padding:3px 8px 3px 0;'>#{b['bet_id']}</td>"
            f"<td style='padding:3px 8px;'>{choice}</td>"
            f"<td style='padding:3px 8px;font-family:JetBrains Mono,monospace;text-align:right;'>{b['bet_amount']:,} coins</td>"
            f"<td style='padding:3px 0 3px 8px;text-align:right;'>"
            f"<span style='display:inline-block;font-size:0.7rem;padding:2px 10px;border-radius:10px;background:{s_color};color:#fff;'>{b['status']}</span></td></tr>"
        )

    st.markdown(f"""
    <div style="flex-basis:100%;padding:0.5rem 0;margin-top:0.25rem;border-top:1px solid var(--border-subtle);">
        <span style="font-family:'Chakra Petch',sans-serif;font-size:0.8rem;color:var(--text-secondary);">Your bets:</span>
        <table style="width:100%;font-family:'Chakra Petch',sans-serif;font-size:0.82rem;color:var(--text-primary);margin-top:4px;">
            {''.join(rows)}
        </table>
    </div>
    """, unsafe_allow_html=True)
```

- [ ] **Step 3: Verify syntax**

```bash
python -c "import ast; ast.parse(open('world_cup/betting_ui.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Test manually (no test suite for UI)**

Run the app and verify:
- Match with no bets → shows "Place Bet →" button, expands slip
- Match with 1+ bets → shows existing bets list, shows "Place Another Bet →" button
- Can place multiple bets on same match (both 1X2 and Handicap)
- Existing bets appear in the list after placement

- [ ] **Step 5: Commit**

```bash
git add world_cup/betting_ui.py
git commit -m "feat: allow multiple bets per match, remove 1-bet lock"
```

---

### Task 2: Tests

**Files:**
- Modify: `world_cup/tests/test_db.py` (add multi-bet tests)

- [ ] **Step 1: Add multi-bet test**

Append to `world_cup/tests/test_db.py`:

```python
# ===========================================================================
# Multi-bet per match
# ===========================================================================

def test_place_multiple_bets_same_match():
    """User can place multiple 1X2 bets on the same match."""
    uid = db_module.register_user("+84multi00001", "Multi1")
    db_module.upsert_match(700, "Brazil", "Thailand", "2026-06-20T18:00:00Z")

    bet1 = db_module.place_bet(uid, 700, "A", 100)
    bet2 = db_module.place_bet(uid, 700, "DRAW", 50)
    bet3 = db_module.place_bet(uid, 700, "A", 30)

    assert bet1 != bet2 != bet3
    assert db_module.get_user_coins(uid) == 820  # 1000 - 100 - 50 - 30

    # All 3 bets exist
    conn = db_module.get_connection()
    bets = conn.execute(
        "SELECT * FROM bets WHERE user_id = ? AND match_id = ?", (uid, 700)
    ).fetchall()
    conn.close()
    assert len(bets) == 3


def test_place_multiple_bets_mixed_markets():
    """User can mix 1X2 and handicap bets on the same match."""
    uid = db_module.register_user("+84multi00002", "Multi2")
    db_module.upsert_match(
        701, "Germany", "Japan", "2026-06-21T18:00:00Z",
    )
    # Set handicap on the match via admin
    db_module.admin_update_match(
        701, "Germany", "Japan", "2026-06-21T18:00:00Z",
        "Not Started", None,
        handicap_line=1.5, handicap_favorite="A", handicap_fee=5,
    )

    bet1 = db_module.place_bet(uid, 701, "A", 100)  # 1X2
    bet2 = db_module.place_handicap_bet(uid, 701, "favorite", 100, 1.5, 5)  # Handicap

    assert bet1 != bet2
    assert db_module.get_user_coins(uid) == 800  # 1000 - 100 - 100

    conn = db_module.get_connection()
    bets = conn.execute(
        "SELECT market FROM bets WHERE user_id = ? AND match_id = ? ORDER BY bet_id",
        (uid, 701),
    ).fetchall()
    conn.close()
    markets = [b["market"] for b in bets]
    assert "1X2" in markets
    assert "handicap" in markets


def test_settle_multiple_bets_same_user():
    """All of a user's bets on a match settle correctly."""
    uid = db_module.register_user("+84multi00003", "Multi3")
    db_module.upsert_match(702, "Brazil", "Thailand", "2026-06-22T18:00:00Z")

    # 2 winning bets, 1 losing bet
    db_module.place_bet(uid, 702, "A", 100)
    db_module.place_bet(uid, 702, "A", 50)
    db_module.place_bet(uid, 702, "B", 30)

    db_module.settle_match_bets(702, "A_win")

    # Won: 100*2 + 50*2 = 300. Lost: 30. Net: 1000 - 180 + 300 = 1120
    assert db_module.get_user_coins(uid) == 1120

    conn = db_module.get_connection()
    bets = conn.execute(
        "SELECT bet_choice, status FROM bets WHERE user_id = ? AND match_id = ? ORDER BY bet_id",
        (uid, 702),
    ).fetchall()
    conn.close()
    assert bets[0]["status"] == "Won"
    assert bets[1]["status"] == "Won"
    assert bets[2]["status"] == "Lost"
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest world_cup/tests/test_db.py -v -k "multi"
```
Expected: 3 tests pass.

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest world_cup/tests/ -v
```
Expected: All existing tests + 3 new tests pass.

- [ ] **Step 4: Commit**

```bash
git add world_cup/tests/test_db.py
git commit -m "test: add multi-bet per match tests"
```

---

## Self-Review

1. **Spec coverage:**
   - Use `fetchall()` instead of `fetchone()` → Task 1 Step 1 ✓
   - Existing bets list → Task 1 Step 2 ✓
   - "Place Another Bet" always visible → Task 1 Step 1 ✓
   - Market selector always shown when handicap exists → Task 1 Step 1 ✓
   - Multi-bet settlement → Task 2 (tests prove it works) ✓
   - No DB changes → confirmed, no migration ✓

2. **Placeholder scan:** No TBDs, TODOs, or vague steps. All code is shown.

3. **Type consistency:**
   - `existing_bets` is `list[sqlite3.Row]` from `fetchall()` — consistently used
   - `has_bets` is `bool` — used for conditional display and button label
   - `_render_existing_bets` signature: `(bets: list, m: dict)` — matches call site
   - Market selector `is_handicap` → `_render_handicap_bet_slip()` matches the function from handicap plan
