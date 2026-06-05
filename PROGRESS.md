# World Cup 2026 — Internal Betting Game

## Progress Log

### 2026-06-05 — Session Summary

---

## Features Added (2026-06-05)

| # | Commit | Feature |
|---|--------|---------|
| 1 | `f2e02b3` | **Handicap betting** — full feature: UI form, settlement logic, admin controls, 6 new tests |
| 2 | `f2e02b3` | **Security hardening** — password auth, HTML escaping, rate limiting, session timeout |
| 3 | `f2e02b3` | **Player buy coins** — sidebar form with confirm flow → admin approve/reject |
| 4 | `f2e02b3` | **Purchase request system** — request queue, admin approve/reject, status tracking |
| 5 | `f2e02b3` | **Admin UI redesign** — black/white theme, phone search for buy coins, cleaned up all tabs |
| 6 | `f2e02b3` | **Match card unification** — betting game uses same match-card CSS as Overview tab |
| 7 | `0ff87cd` | **Quick-add buttons fixed** — +10/+50/+100 now accumulate correctly via shared widget key |

---

## Bug Fixes (2026-06-05)

| # | Commit | Issue | Fix |
|---|--------|-------|-----|
| 1 | `0ff87cd` | Quick-add buttons not updating bet amount | Buttons wrote to `amt_key` but number_input reads from `num_key`. Unified to single session state key. Also fixed handicap bet slip. |
| 2 | `f2e02b3` | `'sqlite3.Row' object has no attribute 'get'` in My Bets | Replaced `.get()` with bracket access for `market`, `handicap_side`, `handicap_line` |
| 3 | `f2e02b3` | 0-coin player crash on bet | Guard `coins < 10` before rendering number_input to avoid `min > max` error |

---

## Security Hardening

| Layer | Implementation |
|-------|---------------|
| **Passwords** | PBKDF2-SHA256 (600K iterations) with per-user salt. `password_hash` column. Backward compat for existing users (prompt to set password). Admin-created users default to `123123`. |
| **HTML escaping** | `html.escape()` on all user names + team names rendered via `unsafe_allow_html=True` |
| **Rate limiting** | Max 10 bets/min per user (in-memory). `_reset_rate_limits()` for tests. |
| **Session timeout** | 60 min idle → auto-logout via `_last_activity` timestamp |
| **Admin safety** | `password_hash` excluded from admin user list |

---

## Handicap Betting

| Component | What |
|-----------|------|
| `game.py` | `settle_handicap_bet()` — win/loss from scores, handicap line, favorite side |
| `betting_ui.py` | `_render_handicap_bet_slip()` — full form with payout preview, quick-add buttons |
| `db.py` | `settle_match_bets()` branches on `bet["market"]`, skips handicap bets without score data |
| `admin.py` | Add/Edit match forms include handicap line, favorite, fee + score fields |
| `test_game.py` | 6 new tests: favorite covers, fails to cover, underdog wins, draw, no scores, favorite=B |

---

## Purchase Request Flow

```
Player (sidebar) → "Send Request" → Confirm popup → DB (purchase_requests, status=pending)
                                                              ↓
Admin (Users tab) → Pending Requests list → [Approve] / [Reject]
                                                              ↓
                                              Approve → credits coins + logs transaction
                                              Reject  → marks rejected, no coins
```

New table: `purchase_requests` (req_id, user_id, vnd_amount, coin_amount, status, created_at, processed_at)

---

## Admin Panel (Redesigned)

- Single `ADMIN_CSS` block with `.admin-root` wrapper — black bg, white text throughout
- All selects/inputs styled: black `#0a0a0a` background, white text
- Buy Coins: phone search via text input → radio select → confirm checkbox → credit
- Pending request approval section above manual credit form
- Purchases tab shows completed transactions + request history
- All edit sections use searchable selectboxes with descriptive labels

---

## Betting UI Changes

- Match display unified with Overview tab's `match_card_db()` CSS
- Quick-add buttons: `[+10] [+50] [+100]` in horizontal row, accumulate on click
- Buy Coins: sidebar form always visible while on Betting Game tab
- 0-coin players see clear error instead of crash
- Removed "Data via football-data.org" from title bar

---

## Test Coverage

```bash
# All tests (skip tests needing pytest-mock)
python -m pytest world_cup/tests/ -v -k "not sync_matches and not test_api"
# → 54 passed (26 game + 28 db)

# Full pipeline
python world_cup/tests/test_full_pipeline.py
# → Alice: 1405 coins, Bob: 850 coins [WIN]
```

---

## How to Run

```bash
# Install
pip install streamlit requests python-dotenv

# Set secrets in .env
API_FOOTBALL_KEY=your_key
ADMIN_PIN=your_pin

# Run main dashboard
streamlit run world_cup/app.py
```

## Admin PIN

Default: `thihq@1010` (set via `.env`: `ADMIN_PIN=yourpin`)

## Exchange Rate

**1,000 VND = 1 coin** — minimum purchase 100,000 VND (100 coins)
