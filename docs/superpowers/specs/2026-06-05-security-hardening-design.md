# Security Hardening — Approach A (Minimal)

**Date:** 2026-06-05  
**Scope:** Public Streamlit betting app, virtual coins, single admin

## 1. Password Authentication

- Add `password_hash` TEXT column to `users` table
- On register: hash password with `bcrypt` via `hashlib` (stdlib, no new dep)
- On login: verify password against stored hash
- Existing users (no password): prompt to set password on first login
- Fallback: if `password_hash` is NULL, skip password check (backward compat)

## 2. Input Sanitization

- Escape HTML in `full_name` and `phone` before rendering
- Use `st.markdown` with `unsafe_allow_html=False` for user-generated content
- Add `html.escape()` call on all user-provided strings before display

## 3. Rate Limiting

- Per-user bet limit: max 10 bets/minute tracked in session state
- Failed login limit: max 5 attempts/minute per phone (in-memory dict, resets on restart)
- Admin PIN: existing 3-attempt/60s lockout stays

## 4. Session Security

- Add session timeout: after 60min idle, clear `st.session_state.user`
- Track `last_activity` timestamp in session state
- Check on each rerender

## 5. Secrets Migration

- Move `ADMIN_PIN` and `API_FOOTBALL_KEY` from `.env` to `st.secrets`
- Keep `.env` fallback for local dev
- Add `.env` to `.gitignore` if not already

## Files Changed

| File | Changes |
|------|---------|
| `db.py` | `password_hash` migration, `register_user()` hashes password, `get_user_by_phone()` returns hash, new `verify_password()` |
| `betting_ui.py` | Login form requires password, HTML-escape user names, session timeout check |
| `app.py` | Session timeout logic, `last_activity` tracking |
| `.env` | Document secrets format |

## Not In Scope

- Multi-admin support
- CAPTCHA
- IP-based rate limiting
- Encrypted DB
- OAuth

## Dependencies

- No new packages. `hashlib` is stdlib. bcrypt via SHA-256 + salt (60k iterations).
