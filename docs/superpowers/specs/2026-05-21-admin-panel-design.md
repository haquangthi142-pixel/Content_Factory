# Admin Panel — Design

## Overview
Add a PIN-protected admin panel to the World Cup 2026 dashboard. The admin can browse, edit, insert, and delete rows across all 5 database tables.

## Access
- New sidebar option "Admin" added to the navigation radio in `app.py`.
- Selecting it shows a centered PIN input field. On correct PIN, the admin panel renders.
- PIN source: `st.secrets["ADMIN_PIN"]` with `.env` fallback (`ADMIN_PIN`).
- PIN check lives in session state so re-runs don't re-prompt.

## New module: `world_cup/admin.py`
Contains `render_admin()` — the full admin UI. Organized as tabs, one per table:

### Tab 1: Users (`users`)
- View all users in a table (id, phone, name, coins, created_at)
- Edit: inline form to change name, phone, coins
- Delete: button with confirmation checkbox per row
- Add: form at top to insert new user (phone, name, starting coins)

### Tab 2: Matches (`matches`)
- View all matches (match_id, team_a, team_b, match_time, status, result)
- Edit: form to change any field
- Delete: button with confirmation
- Add: form to manually insert a match
- Sync button to pull latest from football-data.org API

### Tab 3: Bets (`bets`)
- View all bets joined with user name and match info
- Edit: change bet_choice, bet_amount, status
- Delete: button with confirmation

### Tab 4: Transactions (`coin_transactions`)
- View all transactions (read-only audit trail)
- Delete: button with confirmation (for cleanup)

### Tab 5: Missions (`mission_logs`)
- View all mission logs
- Delete: button with confirmation

## Database helpers added to `world_cup/db.py`
- `admin_get_all_users()` → list of dicts
- `admin_update_user(id, phone, name, coins)`
- `admin_delete_user(id)` — cascades to bets, transactions, mission_logs
- `admin_get_all_matches()` → list of dicts
- `admin_update_match(id, ...)`
- `admin_delete_match(id)` — cascades to bets
- `admin_get_all_bets()` → list of dicts with user/match names
- `admin_update_bet(id, choice, amount, status)`
- `admin_delete_bet(id)`
- `admin_get_all_transactions()` → list of dicts
- `admin_delete_transaction(id)`
- `admin_get_all_missions()` → list of dicts
- `admin_delete_mission(id)`

## Changes to `world_cup/app.py`
- Add "Admin" to sidebar radio options
- Import `render_admin` from `world_cup.admin`
- Call `render_admin()` when view == "Admin"

## UI patterns
- Each tab: `st.dataframe` for browsing with row count summary
- Edit: expander per row or a simple form with pre-filled values
- Delete: `st.checkbox("Confirm delete")` + `st.button("Delete", type="primary")` with red styling
- Add: `st.form` at the top of the tab
- All mutations call `st.rerun()` after success
- Errors surfaced via `st.error()`

## Edge cases
- Cascading deletes: deleting a user removes their bets, transactions, and mission logs. Deleting a match removes bets on that match.
- Empty tables show `st.info("No data")` instead of crashing.
- PIN entry: masked input (`type="password"`), max 3 attempts before cooldown message.
