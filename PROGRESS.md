# World Cup 2026 — Internal Betting Game

## Progress Log

### 2026-06-04 — Session Summary

---

## Bug Fixes

| # | Commit | Issue | Fix |
|---|--------|-------|-----|
| 1 | `89901ab` | Login button not working in embedded betting tab | `st.session_state.user` was unconditionally overwritten by `betting_user` (always `None`) on every rerun |
| 2 | `e3f5c23` | `st.session_state has no attribute "user"` | Missing initialization — added alongside `betting_user` |
| 3 | `8fcbc8c` | `'sqlite3.Row' object has no attribute 'get'` | Replaced `.get()` with bracket access on DB rows; renamed "Place Bet" → "Bet" |
| 4 | `0037b3b` | Admin panel crash on duplicate phone | Added `get_user_by_phone()` check before creating new user |

---

## Features Added

| # | Commit | Feature |
|---|--------|---------|
| 1 | `0f532c4` | Full pipeline test + wired `settle_match_bets` into admin Save/⚡Settle button |
| 2 | `14d4ffd` | **5% house fee** on winning bets (gross payout − 5%) |
| 3 | `cdd4228` | Updated DB unit tests for 5% fee |
| 4 | `4bdd698` | **Auto-sync matches** from football-data.org on player sign-in (once per session) |
| 5 | `dde98d9` | **Hide Leaderboard & Missions** from regular players — admin only |
| 6 | `c64a72b`–`17988af` | **Coin Economy Rework** (see below) |

---

## Coin Economy Rework

### What changed:
| Before | After |
|--------|-------|
| 1,000 free coins on registration | **10 free coins** (1 minimum bet) |
| No way to buy coins | Admin **Buy Coins** form: VND → coins (1,000 VND = 1 coin, min 100K) |
| Daily inactivity penalty (10%) | **Removed** |
| No purchase tracking | **Purchases tab** in admin |

### Commits:
- `c64a72b` — Remove penalty from `game.py`
- `3c64f2f` — 10 free coins, remove penalty from `db.py`, add `purchase_coins()`
- `3594584` — Admin buy-coins form + Purchases tab
- `1f0df7f` — Remove penalty tests from `test_game.py`
- `f623004` — Update `test_db.py` for 10 coins
- `17988af` — Update `test_full_pipeline.py` coin baseline

---

## How to Run

```bash
# Install
pip install streamlit requests python-dotenv

# Set API key in .env
API_FOOTBALL_KEY=your_key
ADMIN_PIN=your_pin

# Run main dashboard
streamlit run world_cup/app.py

# Run standalone betting game
streamlit run world_cup/betting_app.py
```

## How to Test

```bash
# Unit tests
python -m pytest world_cup/tests/ -v -k "not sync_matches"

# Full pipeline test
python world_cup/tests/test_full_pipeline.py
```

## Admin PIN

Default: `0000` (set via `.env`: `ADMIN_PIN=yourpin`)

## Exchange Rate

**1,000 VND = 1 coin** — minimum purchase 100,000 VND (100 coins)
