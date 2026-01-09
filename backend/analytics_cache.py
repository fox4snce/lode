"""
Server-side analytics cache stored in SQLite.

Why:
- The UI should not recompute analytics on every tab switch.
- Refresh should recompute analytics ONCE, then all tabs should be up-to-date.
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Optional


def ensure_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_cache (
            cache_key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_cache_updated_at ON analytics_cache(updated_at)"
    )


def get_cached(conn: sqlite3.Connection, cache_key: str) -> Optional[Any]:
    ensure_cache_table(conn)
    row = conn.execute(
        "SELECT value_json FROM analytics_cache WHERE cache_key = ?",
        (cache_key,),
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def set_cached(conn: sqlite3.Connection, cache_key: str, value: Any) -> None:
    ensure_cache_table(conn)
    payload = json.dumps(value)
    now = time.time()
    conn.execute(
        """
        INSERT INTO analytics_cache(cache_key, value_json, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            value_json=excluded.value_json,
            updated_at=excluded.updated_at
        """,
        (cache_key, payload, now),
    )


def clear_cache(conn: sqlite3.Connection) -> None:
    ensure_cache_table(conn)
    conn.execute("DELETE FROM analytics_cache")

