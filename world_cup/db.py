import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timezone

from world_cup import game

# ---------------------------------------------------------------------------
# Password hashing (stdlib only)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-SHA256 + salt. Returns 'salt$hash'."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored 'salt$hash' string."""
    try:
        salt, stored_hash = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
        return secrets.compare_digest(dk.hex(), stored_hash)
    except (ValueError, AttributeError):
        return False

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            phone           TEXT    UNIQUE NOT NULL,
            full_name       TEXT    NOT NULL,
            current_coins   INTEGER NOT NULL DEFAULT 10,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS matches (
            match_id        INTEGER PRIMARY KEY,
            team_a          TEXT    NOT NULL,
            team_b          TEXT    NOT NULL,
            match_time      TEXT    NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'Not Started',
            result          TEXT
        );

        CREATE TABLE IF NOT EXISTS bets (
            bet_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            match_id        INTEGER NOT NULL REFERENCES matches(match_id),
            bet_choice      TEXT    NOT NULL CHECK (bet_choice IN ('A', 'B', 'DRAW')),
            bet_amount      INTEGER NOT NULL CHECK (bet_amount > 0 AND bet_amount % 10 = 0),
            status          TEXT    NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Won', 'Lost', 'Refunded')),
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            settled_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS coin_transactions (
            tx_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            amount          INTEGER NOT NULL,
            type            TEXT    NOT NULL CHECK (type IN ('bet', 'win', 'penalty', 'mission', 'refund', 'initial', 'free_trial', 'purchase')),
            description     TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS mission_logs (
            log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            mission_type    TEXT    NOT NULL,
            reward_coins    INTEGER NOT NULL,
            completed_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS purchase_requests (
            req_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            vnd_amount      INTEGER NOT NULL,
            coin_amount     INTEGER NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            processed_at    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_bets_user    ON bets(user_id);
        CREATE INDEX IF NOT EXISTS idx_bets_match   ON bets(match_id);
        CREATE INDEX IF NOT EXISTS idx_tx_user      ON coin_transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_tx_created   ON coin_transactions(created_at);
    """)
    # Schema migrations (safe to run repeatedly)
    for _col, _ddl in [
        ("score_a", "ALTER TABLE matches ADD COLUMN score_a INTEGER"),
        ("score_b", "ALTER TABLE matches ADD COLUMN score_b INTEGER"),
        ("handicap_line", "ALTER TABLE matches ADD COLUMN handicap_line REAL"),
        ("handicap_favorite", "ALTER TABLE matches ADD COLUMN handicap_favorite TEXT"),
        ("handicap_fee", "ALTER TABLE matches ADD COLUMN handicap_fee INTEGER DEFAULT 5"),
        ("market", "ALTER TABLE bets ADD COLUMN market TEXT DEFAULT '1X2'"),
        ("handicap_line_bet", "ALTER TABLE bets ADD COLUMN handicap_line REAL"),
        ("handicap_side", "ALTER TABLE bets ADD COLUMN handicap_side TEXT"),
        ("password_hash", "ALTER TABLE users ADD COLUMN password_hash TEXT"),
    ]:
        try:
            conn.execute(_ddl)
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def register_user(phone: str, full_name: str, password: str | None = None) -> int:
    conn = get_connection()
    try:
        pw_hash = hash_password(password) if password else None
        cur = conn.execute(
            "INSERT INTO users (phone, full_name, current_coins, password_hash) VALUES (?, ?, 10, ?)",
            (phone, full_name, pw_hash),
        )
        user_id = cur.lastrowid
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, 10, 'free_trial', 'Free trial coins')",
            (user_id,),
        )
        conn.commit()
        return user_id
    finally:
        conn.close()


def get_user(user_id: int):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()


def get_user_by_phone(phone: str):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
    finally:
        conn.close()


def get_user_coins(user_id: int) -> int:
    row = get_user(user_id)
    return row["current_coins"] if row else 0


def deduct_coins(user_id: int, amount: int, tx_type: str, description: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET current_coins = current_coins - ? WHERE id = ?", (amount, user_id))
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, -?, ?, ?)",
            (user_id, amount, tx_type, description),
        )
        conn.commit()
    finally:
        conn.close()


def add_coins(user_id: int, amount: int, tx_type: str, description: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET current_coins = current_coins + ? WHERE id = ?", (amount, user_id))
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
            (user_id, amount, tx_type, description),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Match sync from API
# ---------------------------------------------------------------------------

def sync_matches_from_api():
    """Pull match data from football-data.org and upsert into the matches table."""
    from world_cup.api import fetch_matches

    data = fetch_matches()
    matches = data.get("matches", [])
    if not matches:
        return 0

    conn = get_connection()
    try:
        for m in matches:
            match_id = m["id"]
            team_a = m["homeTeam"].get("name") or "TBD"
            team_b = m["awayTeam"].get("name") or "TBD"
            match_time = m["utcDate"]

            status_raw = m.get("status", "SCHEDULED")
            if status_raw in ("FINISHED", "AWARDED"):
                status = "Finished"
            elif status_raw in ("LIVE", "IN_PLAY", "PAUSED"):
                status = "Live"
            else:
                status = "Not Started"

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
        return len(matches)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

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


def get_match(match_id: int):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,)).fetchone()
    finally:
        conn.close()


def get_matches_by_date(date_str: str):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM matches WHERE DATE(match_time) = ?", (date_str,)
        ).fetchall()
    finally:
        conn.close()


def get_matches_on_date(date_str: str):
    """Matches that are scheduled on a given date (for penalty check)."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM matches WHERE DATE(match_time) = ?", (date_str,)
        ).fetchall()
    finally:
        conn.close()


def update_match_result(match_id: int, result: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE matches SET result = ?, status = 'Finished' WHERE match_id = ?",
            (result, match_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

_bet_timestamps: dict[int, list[float]] = {}  # user_id -> list of recent bet timestamps
_MAX_BETS_PER_MINUTE = 10

_login_attempts: dict[str, list[float]] = {}  # phone -> list of recent failed login timestamps
_MAX_LOGIN_ATTEMPTS_PER_MINUTE = 5


def _reset_rate_limits():
    """Clear rate-limit state. For tests only."""
    _bet_timestamps.clear()
    _login_attempts.clear()
    _sync_timestamps.clear()


def _check_rate_limit(user_id: int) -> bool:
    """Return True if user is within rate limit, False if exceeded."""
    now = datetime.now(timezone.utc).timestamp()
    stamps = _bet_timestamps.get(user_id, [])
    # Purge old entries
    stamps = [t for t in stamps if now - t < 60]
    _bet_timestamps[user_id] = stamps
    if len(stamps) >= _MAX_BETS_PER_MINUTE:
        return False
    stamps.append(now)
    return True


def check_login_rate_limit(phone: str) -> bool:
    """Return True if login is allowed, False if rate limited (too many failed attempts)."""
    now = datetime.now(timezone.utc).timestamp()
    stamps = _login_attempts.get(phone, [])
    # Purge old entries
    stamps = [t for t in stamps if now - t < 60]
    _login_attempts[phone] = stamps
    if len(stamps) >= _MAX_LOGIN_ATTEMPTS_PER_MINUTE:
        return False
    return True


def record_failed_login(phone: str):
    """Record a failed login attempt for rate limiting."""
    now = datetime.now(timezone.utc).timestamp()
    stamps = _login_attempts.get(phone, [])
    stamps = [t for t in stamps if now - t < 60]
    stamps.append(now)
    _login_attempts[phone] = stamps


_sync_timestamps: dict[int, float] = {}  # user_id -> last sync timestamp
_SYNC_COOLDOWN_SECONDS = 30


def check_sync_rate_limit(user_id: int) -> bool:
    """Return True if the user is allowed to sync matches (max once per 30s)."""
    now = datetime.now(timezone.utc).timestamp()
    last = _sync_timestamps.get(user_id, 0)
    if now - last < _SYNC_COOLDOWN_SECONDS:
        return False
    _sync_timestamps[user_id] = now
    return True


# ---------------------------------------------------------------------------
# Bets
# ---------------------------------------------------------------------------

def place_bet(user_id: int, match_id: int, bet_choice: str, bet_amount: int) -> int:
    if not _check_rate_limit(user_id):
        raise ValueError("Too many bets. Slow down — max 10 bets per minute.")
    conn = get_connection()
    try:
        # Validate bet amount
        ok, err = game.validate_bet_amount(bet_amount)
        if not ok:
            raise ValueError(err)

        # Check user exists and has enough coins
        coins = conn.execute("SELECT current_coins FROM users WHERE id = ?", (user_id,)).fetchone()
        if not coins:
            raise ValueError("User not found")
        if coins["current_coins"] < bet_amount:
            raise ValueError(f"Insufficient coins. You have {coins['current_coins']}. Buy more coins or contact admin.")

        # Check match exists and is not finished
        match = conn.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,)).fetchone()
        if not match:
            raise ValueError("Match not found")
        if match["status"] == "Finished":
            raise ValueError("Cannot bet on a finished match")

        # Deduct coins and place bet
        conn.execute("UPDATE users SET current_coins = current_coins - ? WHERE id = ?",
                     (bet_amount, user_id))
        cur = conn.execute(
            "INSERT INTO bets (user_id, match_id, bet_choice, bet_amount) VALUES (?, ?, ?, ?)",
            (user_id, match_id, bet_choice, bet_amount),
        )
        bet_id = cur.lastrowid
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, -?, 'bet', ?)",
            (user_id, bet_amount, f"Bet on match #{match_id}: {bet_choice}"),
        )
        conn.commit()
        return bet_id
    finally:
        conn.close()


# Re-exported from game.py for backward compatibility
HANDICAP_PAYOUT = game.HANDICAP_PAYOUT
get_handicap_payout = game.get_handicap_payout
calc_handicap_win_amount = game.calc_handicap_win_amount


def place_handicap_bet(user_id: int, match_id: int, handicap_side: str,
                       bet_amount: int, handicap_line: float,
                       handicap_fee: int) -> int:
    if not _check_rate_limit(user_id):
        raise ValueError("Too many bets. Slow down — max 10 bets per minute.")
    conn = get_connection()
    try:
        ok, err = game.validate_bet_amount(bet_amount)
        if not ok:
            raise ValueError(err)

        coins = conn.execute(
            "SELECT current_coins FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not coins:
            raise ValueError("User not found")
        if coins["current_coins"] < bet_amount:
            raise ValueError(f"Insufficient coins. You have {coins['current_coins']}. Buy more coins or contact admin.")

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
            (user_id, match_id, "A", bet_amount, handicap_line, handicap_side),
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


def settle_match_bets(match_id: int, result: str):
    """Settle all pending bets for a match. Handles both 1X2 and handicap markets."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE matches SET result = ?, status = 'Finished' WHERE match_id = ?",
            (result, match_id),
        )
        # Re-fetch match for score data (needed for handicap settlement)
        match = conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()

        pending = conn.execute(
            "SELECT * FROM bets WHERE match_id = ? AND status = 'Pending'", (match_id,)
        ).fetchall()

        for bet in pending:
            if bet["market"] == "handicap":
                # Skip if missing data needed for settlement
                if match["handicap_favorite"] is None or match["score_a"] is None or match["score_b"] is None:
                    continue
                status, payout = game.settle_handicap_bet(
                    bet["handicap_side"], bet["handicap_line"],
                    match["handicap_favorite"], match["score_a"], match["score_b"],
                    bet["bet_amount"], match["handicap_fee"] or 5,
                )
                if status == "Pending":
                    continue
            else:
                status, payout = game.settle_bet(bet["bet_choice"], bet["bet_amount"], result)

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


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def get_leaderboard():
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT id, full_name, current_coins FROM users ORDER BY current_coins DESC"
        ).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

def complete_mission(user_id: int, mission_type: str, reward_coins: int):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO mission_logs (user_id, mission_type, reward_coins) VALUES (?, ?, ?)",
            (user_id, mission_type, reward_coins),
        )
        conn.execute("UPDATE users SET current_coins = current_coins + ? WHERE id = ?",
                     (reward_coins, user_id))
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, 'mission', ?)",
            (user_id, reward_coins, f"Mission: {mission_type}"),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Coin purchases
# ---------------------------------------------------------------------------

def purchase_coins(user_id: int, vnd_amount: int) -> int:
    """Convert VND to coins and credit user. Returns coins credited."""
    coins = vnd_amount // 1000
    if coins <= 0:
        raise ValueError(f"Minimum purchase is 100,000 VND (100 coins). Got {vnd_amount:,} VND.")
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET current_coins = current_coins + ? WHERE id = ?",
                     (coins, user_id))
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, 'purchase', ?)",
            (user_id, coins, f"Purchased {coins} coins ({vnd_amount:,} VND)"),
        )
        conn.commit()
        return coins
    finally:
        conn.close()


def admin_get_purchases():
    """Return all purchase transactions (admin-only view)."""
    conn = get_connection()
    try:
        return _dict_rows(conn.execute(
            """SELECT t.*, u.full_name AS user_name
               FROM coin_transactions t
               JOIN users u ON t.user_id = u.id
               WHERE t.type = 'purchase'
               ORDER BY t.created_at DESC"""
        ).fetchall())
    finally:
        conn.close()


def request_purchase(user_id: int, vnd_amount: int) -> int:
    """Player submits a coin purchase request. Returns request ID."""
    coins = vnd_amount // 1000
    if coins <= 0:
        raise ValueError(f"Minimum purchase is 100,000 VND (100 coins). Got {vnd_amount:,} VND.")
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO purchase_requests (user_id, vnd_amount, coin_amount) VALUES (?, ?, ?)",
            (user_id, vnd_amount, coins),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def admin_get_purchase_requests(status_filter: str | None = None):
    """Return purchase requests. status_filter: 'pending', 'approved', 'rejected', or None for all."""
    conn = get_connection()
    try:
        if status_filter:
            rows = conn.execute(
                """SELECT r.*, u.full_name AS user_name, u.phone
                   FROM purchase_requests r
                   JOIN users u ON r.user_id = u.id
                   WHERE r.status = ?
                   ORDER BY r.created_at DESC""",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT r.*, u.full_name AS user_name, u.phone
                   FROM purchase_requests r
                   JOIN users u ON r.user_id = u.id
                   ORDER BY r.created_at DESC"""
            ).fetchall()
        return _dict_rows(rows)
    finally:
        conn.close()


def admin_approve_purchase_request(req_id: int) -> dict:
    """Approve a purchase request and credit coins. Returns updated request row."""
    conn = get_connection()
    try:
        req = conn.execute(
            "SELECT * FROM purchase_requests WHERE req_id = ?", (req_id,)
        ).fetchone()
        if not req:
            raise ValueError(f"Request #{req_id} not found.")
        if req["status"] != "pending":
            raise ValueError(f"Request #{req_id} is already {req['status']}.")

        conn.execute(
            "UPDATE purchase_requests SET status = 'approved', processed_at = datetime('now') WHERE req_id = ?",
            (req_id,),
        )
        conn.execute("UPDATE users SET current_coins = current_coins + ? WHERE id = ?",
                     (req["coin_amount"], req["user_id"]))
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, 'purchase', ?)",
            (req["user_id"], req["coin_amount"],
             f"Purchased {req['coin_amount']} coins ({req['vnd_amount']:,} VND) [req #{req_id}]"),
        )
        conn.commit()
        return dict(req)
    finally:
        conn.close()


def admin_reject_purchase_request(req_id: int):
    """Reject a purchase request."""
    conn = get_connection()
    try:
        req = conn.execute(
            "SELECT * FROM purchase_requests WHERE req_id = ?", (req_id,)
        ).fetchone()
        if not req:
            raise ValueError(f"Request #{req_id} not found.")
        if req["status"] != "pending":
            raise ValueError(f"Request #{req_id} is already {req['status']}.")

        conn.execute(
            "UPDATE purchase_requests SET status = 'rejected', processed_at = datetime('now') WHERE req_id = ?",
            (req_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------

def _dict_row(row):
    return dict(row) if row else None


def _dict_rows(rows):
    return [dict(r) for r in rows]


# -- Users --

def admin_get_all_users():
    conn = get_connection()
    try:
        return _dict_rows(conn.execute(
            "SELECT id, phone, full_name, current_coins, created_at FROM users ORDER BY id"
        ).fetchall())
    finally:
        conn.close()


def admin_update_user(user_id: int, phone: str, full_name: str, coins: int):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET phone = ?, full_name = ?, current_coins = ? WHERE id = ?",
            (phone, full_name, coins, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def admin_delete_user(user_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM mission_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM coin_transactions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM purchase_requests WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM bets WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# -- Matches --

def admin_get_all_matches():
    conn = get_connection()
    try:
        return _dict_rows(conn.execute("SELECT * FROM matches ORDER BY match_time").fetchall())
    finally:
        conn.close()


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


def admin_delete_match(match_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM bets WHERE match_id = ?", (match_id,))
        conn.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))
        conn.commit()
    finally:
        conn.close()


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


# -- Bets --

def admin_get_all_bets():
    conn = get_connection()
    try:
        return _dict_rows(conn.execute(
            """SELECT b.*, u.full_name AS user_name, m.team_a, m.team_b
               FROM bets b
               JOIN users u ON b.user_id = u.id
               JOIN matches m ON b.match_id = m.match_id
               ORDER BY b.created_at DESC"""
        ).fetchall())
    finally:
        conn.close()


def admin_update_bet(bet_id: int, bet_choice: str, bet_amount: int, status: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE bets SET bet_choice = ?, bet_amount = ?, status = ? WHERE bet_id = ?",
            (bet_choice, bet_amount, status, bet_id),
        )
        conn.commit()
    finally:
        conn.close()


def admin_delete_bet(bet_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM bets WHERE bet_id = ?", (bet_id,))
        conn.commit()
    finally:
        conn.close()


# -- Transactions --

def admin_get_all_transactions():
    conn = get_connection()
    try:
        return _dict_rows(conn.execute(
            """SELECT t.*, u.full_name AS user_name
               FROM coin_transactions t
               JOIN users u ON t.user_id = u.id
               ORDER BY t.created_at DESC"""
        ).fetchall())
    finally:
        conn.close()


def admin_delete_transaction(tx_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM coin_transactions WHERE tx_id = ?", (tx_id,))
        conn.commit()
    finally:
        conn.close()


# -- Missions --

def admin_get_all_missions():
    conn = get_connection()
    try:
        return _dict_rows(conn.execute(
            """SELECT m.*, u.full_name AS user_name
               FROM mission_logs m
               JOIN users u ON m.user_id = u.id
               ORDER BY m.completed_at DESC"""
        ).fetchall())
    finally:
        conn.close()


def admin_delete_mission(log_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM mission_logs WHERE log_id = ?", (log_id,))
        conn.commit()
    finally:
        conn.close()
