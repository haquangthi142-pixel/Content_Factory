# Multi-Bet Per Match — Design Spec

**Date:** 2026-06-04
**Status:** Draft

## Summary

Remove the current 1-bet-per-match restriction. Users can place unlimited bets on a single match, mixing 1X2 and Handicap markets freely. All bets are immutable once placed — no editing, no deleting.

## Constraint

- Bets cannot be modified after placement (no change to this rule)
- No limit on number of bets per match
- Can mix markets (1X2 + Handicap on same match)
- Can bet same choice multiple times (e.g., two "Brazil Win" bets at different amounts)

## Database

No schema changes. The `bets` table already supports multiple rows per `(user_id, match_id)` combination — the 1-bet limit was purely a UI/validation constraint.

```sql
-- No migration needed. Existing table:
CREATE TABLE bets (
    bet_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    match_id   INTEGER NOT NULL REFERENCES matches(match_id),
    bet_choice TEXT    NOT NULL,
    bet_amount INTEGER NOT NULL,
    market     TEXT    DEFAULT '1X2',
    ...
);
-- No unique constraint on (user_id, match_id) — multi-bet already possible at DB level
```

## UI Changes

### Match Card (with existing bets)

When user already bet on this match, render a compact list of their bets:

```
Match Card: Brazil vs Thailand · 20:00 UTC
  ┌─────────────────────────────────────────────────┐
  │ Your bets:                                       │
  │  #1 · 1X2 · Brazil Win · 100 coins              │
  │  #2 · Handicap · Underdog +1.5 · 50 coins       │
  └─────────────────────────────────────────────────┘
  [+ Place Another Bet]
```

Clicking "+ Place Another Bet" expands the betting slip below — same as current expand/collapse behavior.

### Match Card (no existing bets)

Unchanged — shows "Place Bet →" button that expands the slip.

### Betting Slip

Market selector (1X2 / Handicap) always shown when match has handicap set. Each new bet starts fresh — no carryover from previous bets.

### Bet History (My Bets tab)

Grouped display option: show all bets with newest first, grouped by match. Each bet is its own row. No change to settlement status display.

## Files to Modify

| File | Change |
|---|---|
| `world_cup/betting_ui.py` | `_render_match_fixture()` — use `fetchall()`, render existing bets list, always show "Place Another Bet". Add `_render_existing_bets()` helper. |
| `world_cup/betting_ui.py` | `_render_bet_slip()` — always show market selector when handicap exists (currently only shown on first bet). |

Files NOT modified: `db.py`, `game.py`, `admin.py`, `app.py`, `betting_app.py`.

## Settlement

No change. `settle_match_bets()` already loops all pending bets for the match — it naturally handles multiple bets per user.

## Testing

- Place 2 bets on same match (same market, same choice) → both recorded
- Place 2 bets on same match (different markets) → both recorded
- Settlement: all user's bets on a match settle correctly
- Existing bets list renders correctly with 0, 1, 3 bets
- "Place Another Bet" button always visible when match has existing bets

## Out of Scope

- Editing/deleting existing bets
- Bet limits per match
- Combined/multi-bet slips (parlay)
