import sqlite3
import os
from datetime import datetime, timezone

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
            current_coins   INTEGER NOT NULL DEFAULT 1000,
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
            type            TEXT    NOT NULL CHECK (type IN ('bet', 'win', 'penalty', 'mission', 'refund', 'initial')),
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

        CREATE INDEX IF NOT EXISTS idx_bets_user    ON bets(user_id);
        CREATE INDEX IF NOT EXISTS idx_bets_match   ON bets(match_id);
        CREATE INDEX IF NOT EXISTS idx_tx_user      ON coin_transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_tx_created   ON coin_transactions(created_at);
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def register_user(phone: str, full_name: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (phone, full_name, current_coins) VALUES (?, ?, 1000)",
            (phone, full_name),
        )
        user_id = cur.lastrowid
        conn.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, 1000, 'initial', 'Starting capital')",
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

            conn.execute("""
                INSERT INTO matches (match_id, team_a, team_b, match_time, status, result)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    team_a    = excluded.team_a,
                    team_b    = excluded.team_b,
                    match_time = excluded.match_time,
                    status    = excluded.status,
                    result    = excluded.result
            """, (match_id, team_a, team_b, match_time, status, result))

        conn.commit()
        return len(matches)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

def upsert_match(match_id: int, team_a: str, team_b: str, match_time: str,
                 status: str = "Not Started", result: str = None):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO matches (match_id, team_a, team_b, match_time, status, result)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                team_a    = excluded.team_a,
                team_b    = excluded.team_b,
                match_time = excluded.match_time,
                status    = excluded.status,
                result    = excluded.result
        """, (match_id, team_a, team_b, match_time, status, result))
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
# Bets
# ---------------------------------------------------------------------------

def place_bet(user_id: int, match_id: int, bet_choice: str, bet_amount: int) -> int:
    conn = get_connection()
    try:
        # Validate bet amount is multiple of 10
        if bet_amount <= 0 or bet_amount % 10 != 0:
            raise ValueError("Bet amount must be a positive multiple of 10")

        # Check user has enough coins
        coins = conn.execute("SELECT current_coins FROM users WHERE id = ?", (user_id,)).fetchone()
        if not coins:
            raise ValueError("User not found")
        if coins["current_coins"] < bet_amount:
            raise ValueError(f"Insufficient coins. You have {coins['current_coins']}.")

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


def settle_match_bets(match_id: int, result: str):
    """Settle all pending bets for a match when result is known (A_win, B_win, Draw)."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE matches SET result = ?, status = 'Finished' WHERE match_id = ?",
            (result, match_id),
        )
        pending = conn.execute(
            "SELECT * FROM bets WHERE match_id = ? AND status = 'Pending'", (match_id,)
        ).fetchall()

        for bet in pending:
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

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Daily penalty
# ---------------------------------------------------------------------------

def apply_daily_penalty(date_str: str):
    """Deduct 10% from users who didn't bet on a match day."""
    conn = get_connection()
    try:
        matches_today = conn.execute(
            "SELECT COUNT(*) as cnt FROM matches WHERE DATE(match_time) = ?", (date_str,)
        ).fetchone()
        if not matches_today or matches_today["cnt"] == 0:
            conn.close()
            return 0  # No matches today, no penalty

        users = conn.execute("SELECT id, current_coins FROM users").fetchall()
        penalized = 0

        for user in users:
            has_bet = conn.execute(
                """SELECT COUNT(*) as cnt FROM bets
                   WHERE user_id = ? AND DATE(created_at) = ?""",
                (user["id"], date_str),
            ).fetchone()

            if not has_bet or has_bet["cnt"] == 0:
                penalty = max(10, user["current_coins"] // 10)  # At least 10 coins
                if penalty % 10 != 0:
                    penalty = ((penalty // 10) + 1) * 10  # Round up to multiple of 10
                actual_penalty = min(penalty, user["current_coins"])  # Don't go below 0

                if actual_penalty > 0:
                    conn.execute(
                        "UPDATE users SET current_coins = current_coins - ? WHERE id = ?",
                        (actual_penalty, user["id"]),
                    )
                    conn.execute(
                        "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, -?, 'penalty', ?)",
                        (user["id"], actual_penalty, f"10% inactivity penalty for {date_str}"),
                    )
                    penalized += 1

        conn.commit()
        return penalized
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
        return _dict_rows(conn.execute("SELECT * FROM users ORDER BY id").fetchall())
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
                       status: str, result: str | None):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE matches SET team_a = ?, team_b = ?, match_time = ?, status = ?, result = ? WHERE match_id = ?",
            (team_a, team_b, match_time, status, result, match_id),
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
                       status: str = "Not Started", result: str | None = None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO matches (match_id, team_a, team_b, match_time, status, result) VALUES (?, ?, ?, ?, ?, ?)",
            (match_id, team_a, team_b, match_time, status, result),
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
