"""Tiny SQLite-backed callback scheduler. One table, no ORM needed."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "callbacks.db"


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS callbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_phone_number TEXT NOT NULL,
                requested_time_raw TEXT NOT NULL,
                parsed_datetime TEXT NOT NULL,
                barrier TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )


def add_callback(
    caller_phone_number: str,
    requested_time_raw: str,
    parsed_datetime: str,
    barrier: str = "",
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO callbacks
                (caller_phone_number, requested_time_raw, parsed_datetime, barrier, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                caller_phone_number,
                requested_time_raw,
                parsed_datetime,
                barrier,
                datetime.utcnow().isoformat(),
            ),
        )
        return cur.lastrowid


def list_callbacks(status: str = "pending") -> list[dict]:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM callbacks WHERE status = ? ORDER BY parsed_datetime ASC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]
