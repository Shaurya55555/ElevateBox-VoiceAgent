"""Callback + idempotency store.

SQLite by default (zero setup, fine locally). Set DATABASE_URL to a
Postgres URL (Render free Postgres works) and the same code uses Postgres,
so callbacks and processed-event keys survive restarts and redeploys.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = "callbacks.db"


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


def using_postgres() -> bool:
    return _database_url().startswith(("postgres://", "postgresql://"))


@contextmanager
def _conn():
    if using_postgres():
        import psycopg2  # lazy: only needed when DATABASE_URL is set

        conn = psycopg2.connect(_database_url())
    else:
        conn = sqlite3.connect(os.environ.get("CALLBACKS_DB_PATH", DB_PATH))
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _sql(query: str) -> str:
    """Write queries with ? placeholders; convert for Postgres."""
    return query.replace("?", "%s") if using_postgres() else query


def _execute(conn, query: str, params: tuple = ()):
    cur = conn.cursor()
    cur.execute(_sql(query), params)
    return cur


def init_db() -> None:
    pk = "SERIAL PRIMARY KEY" if using_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    with _conn() as conn:
        _execute(conn, f"""
            CREATE TABLE IF NOT EXISTS callbacks (
                id {pk},
                caller_phone_number TEXT NOT NULL,
                requested_time_raw TEXT NOT NULL,
                parsed_datetime TEXT NOT NULL,
                barrier TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )""")
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS processed_events (
                event_key TEXT PRIMARY KEY,
                result TEXT,
                created_at TEXT NOT NULL
            )""")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_callback(caller_phone_number: str, requested_time_raw: str,
                 parsed_datetime: str, barrier: str = "") -> int:
    with _conn() as conn:
        if using_postgres():
            cur = _execute(conn, """
                INSERT INTO callbacks (caller_phone_number, requested_time_raw,
                    parsed_datetime, barrier, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?) RETURNING id""",
                (caller_phone_number, requested_time_raw, parsed_datetime, barrier, _now()))
            return cur.fetchone()[0]
        cur = _execute(conn, """
            INSERT INTO callbacks (caller_phone_number, requested_time_raw,
                parsed_datetime, barrier, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)""",
            (caller_phone_number, requested_time_raw, parsed_datetime, barrier, _now()))
        return cur.lastrowid


def list_callbacks(status: str = "pending") -> list[dict]:
    with _conn() as conn:
        cur = _execute(conn, "SELECT id, caller_phone_number, requested_time_raw, "
                       "parsed_datetime, barrier, status, created_at FROM callbacks "
                       "WHERE status = ? ORDER BY parsed_datetime ASC", (status,))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_event(event_key: str) -> dict | None:
    """Return the stored result for an already-processed event, else None."""
    with _conn() as conn:
        cur = _execute(conn, "SELECT result FROM processed_events WHERE event_key = ?",
                       (event_key,))
        row = cur.fetchone()
    if row is None:
        return None
    return json.loads(row[0]) if row[0] else {}


def save_event(event_key: str, result: dict | None = None) -> None:
    with _conn() as conn:
        if using_postgres():
            _execute(conn, "INSERT INTO processed_events (event_key, result, created_at) "
                     "VALUES (?, ?, ?) ON CONFLICT (event_key) DO NOTHING",
                     (event_key, json.dumps(result or {}), _now()))
        else:
            _execute(conn, "INSERT OR IGNORE INTO processed_events "
                     "(event_key, result, created_at) VALUES (?, ?, ?)",
                     (event_key, json.dumps(result or {}), _now()))
