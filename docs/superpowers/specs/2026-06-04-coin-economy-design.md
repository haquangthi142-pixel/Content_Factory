# Coin Economy Rework

**Date:** 2026-06-04
**Status:** Approved

## Overview

Replace the 1000-coin starting capital with a free-trial + purchase model using VND.

## Details

### Free Trial
- 10 coins on registration (was 1000). Enough for 1 minimum bet.
- Transaction type: `free_trial`

### Buy Coins (Admin Only)
- Exchange rate: 1,000 VND = 1 coin
- Admin enters VND amount in admin panel (min 100,000 VND = 100 coins)
- System calculates coins = VND / 1000
- Credits user balance, logs transaction type `purchase`
- Purchase history viewable by admin only

### Removals
- Daily inactivity penalty (all penalty functions removed)
- Missions tab hidden from players
- 1000-coin initial capital

### Files Changed
- `db.py`: DEFAULT 10, remove penalty, add purchase_coins, add purchases tracking
- `game.py`: Remove penalty functions (calc_penalty_amount, calc_users_to_penalize)
- `admin.py`: Add buy-coins form + purchase history table
- `betting_ui.py`: Update "out of coins" message
- Tests: Update expected values (1000→10), remove penalty tests

### Edge Cases
- Purchase min: 100,000 VND enforced in admin form
- Bet max: user's current coins (no borrowing)
- No negative balances
