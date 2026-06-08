"""Turso database wrapper — sqlite3-compatible API backed by libsql_client.

When TURSO_URL and TURSO_AUTH_TOKEN are configured (via .env or st.secrets),
get_connection() returns a TursoConnection that talks to the cloud database.
Otherwise it falls back to local SQLite.

Usage: identical to sqlite3 — just call get_connection() and use .execute(),
.fetchone(), .fetchall(), .commit(), .close() as usual.
"""

import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game.db")

TURSO_URL = os.getenv("TURSO_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

try:
    import streamlit as st
    TURSO_URL = st.secrets.get("TURSO_URL", TURSO_URL)
    TURSO_AUTH_TOKEN = st.secrets.get("TURSO_AUTH_TOKEN", TURSO_AUTH_TOKEN)
except Exception:
    pass

_USE_TURSO = bool(TURSO_URL and TURSO_AUTH_TOKEN)


# ---------------------------------------------------------------------------
# Turso row / cursor / connection wrappers
# ---------------------------------------------------------------------------

class _TursoRow:
    """Thin wrapper so libsql Row behaves like sqlite3.Row (index + key access)."""

    def __init__(self, libsql_row, columns):
        self._row = libsql_row
        self._cols = columns
        self._map = {col: libsql_row[i] for i, col in enumerate(columns)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        return self._map[key]

    def __iter__(self):
        return iter(self._row)

    def keys(self):
        return self._cols

    def __repr__(self):
        return f"TursoRow({self._map})"


class _TursoCursor:
    """Mimics sqlite3.Cursor — returned by TursoConnection.execute()."""

    def __init__(self, result_set=None):
        if result_set is not None:
            rs = result_set
            self._rows = [_TursoRow(r, rs.columns) for r in rs.rows] if rs.rows else []
            self.lastrowid = rs.last_insert_rowid if rs.last_insert_rowid else None
        else:
            self._rows = []
            self.lastrowid = None

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class TursoConnection:
    """Mimics sqlite3.Connection for Turso/libsql remote database.

    Lazily wraps each batch of writes in a transaction so multi-statement
    operations remain atomic.  Reads go through the current transaction
    when one is active, otherwise execute directly.
    """

    def __init__(self):
        from libsql_client import create_client_sync

        self._client = create_client_sync(
            url=TURSO_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )
        self._tx = None
        self.row_factory = None  # accepted but ignored — rows always dict-like

    def execute(self, sql, params=None):
        args = list(params) if params else None
        # DDL statements must run outside a transaction
        upper = sql.lstrip().upper()
        is_ddl = upper.startswith(("ALTER ", "CREATE ", "DROP "))
        if self._tx is not None and not is_ddl:
            result = self._tx.execute(sql, args)
        else:
            result = self._client.execute(sql, args)
        return _TursoCursor(result)

    def executescript(self, sql):
        """Run DDL statements — always outside a transaction (Turso rejects
        schema changes inside transactions)."""
        stmts = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in stmts:
            self._client.execute(stmt)
        return _TursoCursor()

    def begin(self):
        """Start a new transaction (called automatically on first write when
        using the convenience methods).  Idempotent if already in a tx."""
        if self._tx is None:
            self._tx = self._client.transaction()
            self._tx.__enter__()

    def commit(self):
        """Commit the current transaction (no-op if no active tx)."""
        if self._tx is not None:
            self._tx.commit()
            self._tx = None

    def rollback(self):
        """Roll back the current transaction."""
        if self._tx is not None:
            try:
                self._tx.rollback()
            except Exception:
                pass
            self._tx = None

    def close(self):
        """Close the connection. Uncommitted work is rolled back."""
        self.rollback()
        self._client.close()


# ---------------------------------------------------------------------------
# Entry point — used by db.py instead of sqlite3.connect()
# ---------------------------------------------------------------------------

def get_connection():
    """Return a database connection — Turso if configured, else local SQLite.

    Turso connections auto-start a transaction so multi-statement operations
    remain atomic (matching SQLite's implicit-transaction behaviour).
    Callers MUST call .commit() to persist work; .close() rolls back
    uncommitted work.
    """
    if _USE_TURSO:
        conn = TursoConnection()
        conn.begin()  # match SQLite implicit-transaction semantics
        return conn
    # Local SQLite fallback
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn
