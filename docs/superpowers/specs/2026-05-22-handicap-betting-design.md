# Handicap Betting System — Design Spec

**Date:** 2026-05-22
**Status:** Approved

## Summary

Add a handicap (spread) betting market alongside the existing 1X2 market. Admin sets a half-goal handicap line per match. Users bet on Favorite (gives goals) or Underdog (receives goals). Payout scales with line size. Admin takes a configurable fee from each stake.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Integration | Hybrid (C) | Handicap optional per match; no handicap = 1X2 only |
| Line style | Half-goal only (0.5, 1.5, 2.5, 3.5) | No push/draw in handicap; simpler settlement |
| Payout structure | Fixed by line size | Higher line = higher payout; transparent to users |
| Fee model | Pre-bet commission (A) | Fee deducted from stake before bet; visible in UI |
| DB approach | Inline columns on matches (Approach 1) | Matches existing flat-table patterns; minimal changes |

## Database Changes

### `matches` table — new columns

```sql
ALTER TABLE matches ADD COLUMN handicap_line REAL;       -- e.g., 0.5, 1.5, 2.5, 3.5
ALTER TABLE matches ADD COLUMN handicap_favorite TEXT;    -- 'A' or 'B' (which team gives the handicap)
ALTER TABLE matches ADD COLUMN handicap_fee INTEGER DEFAULT 5;  -- admin fee percent (whole number, e.g., 5 = 5%)
```

### `bets` table — new column

```sql
ALTER TABLE bets ADD COLUMN market TEXT DEFAULT '1X2';    -- '1X2' or 'handicap'
```

### `bets` table — handicap-specific columns

```sql
ALTER TABLE bets ADD COLUMN handicap_line REAL;           -- snapshot of line at bet time
ALTER TABLE bets ADD COLUMN handicap_side TEXT;           -- 'favorite' or 'underdog'
```

If `market = '1X2'`, the existing `bet_choice` column is used. If `market = 'handicap'`, handicap columns drive settlement.

## Payout Tiers

| Handicap Line | Payout Multiplier | Win on 100 coins (5% fee) | Net Profit |
|---|---|---|---|
| ±0.5 | 1.8x | 171 | +71 |
| ±1.5 | 2.5x | 237 | +137 |
| ±2.5 | 3.5x | 332 | +232 |
| ±3.5 | 5.0x | 475 | +375 |

Formula: `payout_amount = floor((wager - fee) * multiplier)`, fee = `floor(wager * fee_percent / 100)`.

## Settlement Logic

When match finishes with goals (home_A, away_B) and handicap_line = L, favorite_team = F:

```
goal_diff = goals_A - goals_B

# If favorite is Team A:
#   Favorite covers if: goal_diff - L > 0
#   Underdog covers if: goal_diff - L < 0

# If favorite is Team B:
#   Convert to same frame:
#   Favorite covers if: -goal_diff - L > 0
#   Underdog covers if: -goal_diff - L < 0
```

Since L is always a half-goal (0.5, 1.5, 2.5, 3.5), the margin can never equal L exactly — no push/refund.

## Admin UI

Extend the existing admin Match editor. When creating/editing a match, add:

- **Handicap Line** dropdown: `None | 0.5 | 1.5 | 2.5 | 3.5`
- **Favorite** dropdown: `Team A | Team B` (only active when line is set)
- **Fee %** number input: default 5, range 1-20

The admin CRUD functions in `db.py` already support column updates — add the new columns to `admin_update_match` and `admin_insert_match`.

## User UI — Betting Slip

When a match has a handicap set, show two market choices above the betting area:

- `○ 1X2 (Win/Draw/Win)` — existing
- `● Handicap` — new

Selecting "Handicap" renders the handicap betting slip with:

1. **Pick side:** Radio buttons — "Team X -L (Favorite)" / "Team Y +L (Underdog)"
2. **Bet amount:** Number input + quick-add buttons (+10, +50, +100)
3. **Bet summary box:**
   - Wager amount
   - Admin fee (X coins)
   - Net at risk
   - Payout rate (Nx)
   - If WIN: total return + profit
   - If LOSE: amount lost
4. **Condition hint:** "Brazil must win by 2+ goals for this bet to win."

Both `betting_app.py` (standalone) and `app.py` (integrated) get this UI.

## Fees & Profit Tracking

The admin fee coins are NOT returned to any user wallet. They are effectively burned/destroyed. As a future enhancement, this could be tracked in a separate "house" ledger, but for now it's implicit (coins deducted but not paid out anywhere).

## Files to Modify

| File | Changes |
|---|---|
| `db.py` | init_db: alter table; add handicap handling to place_bet, settle_match_bets; update admin CRUD |
| `admin.py` | Match editor: handicap fields (line, favorite, fee) |
| `betting_app.py` | Bet betting slip: market selector, handicap slip with profit preview, settlement display |
| `app.py` | Same handicap slip integration in integrated betting view |

## Testing

- Unit tests for settlement math (all 4 line levels × favorite A/B × result combinations)
- Test handicap bet placement validates fee deduction
- Test admin CRUD reads/writes handicap columns
- Test that matches without handicap show only 1X2 market

## Out of Scope

- Quarter-goal lines (0.25, 0.75)
- Multiple handicap lines per match
- Live handicap adjustments during matches
- Admin fee revenue tracking/ledger
