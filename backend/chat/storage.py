"""
SQLite-backed persistence for chat UI state.

We store this in the main Lode database (conversations.db) because:
- it's already initialized before Chat can be accessed
- it's per-user persistent state
"""

from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional


def ensure_chat_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_user_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_provider TEXT,
            last_model TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_verified_models (
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            verified_ok INTEGER NOT NULL DEFAULT 1,
            last_verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (provider, model)
        )
        """
    )
    conn.commit()


def get_settings(conn: sqlite3.Connection) -> Dict[str, Optional[str]]:
    ensure_chat_tables(conn)
    row = conn.execute(
        "SELECT last_provider, last_model FROM chat_user_settings WHERE id = 1"
    ).fetchone()
    if not row:
        return {"last_provider": None, "last_model": None}
    return {"last_provider": row[0], "last_model": row[1]}


def set_last_used(conn: sqlite3.Connection, provider: str, model: str) -> None:
    ensure_chat_tables(conn)
    conn.execute(
        """
        INSERT INTO chat_user_settings (id, last_provider, last_model, updated_at)
        VALUES (1, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            last_provider=excluded.last_provider,
            last_model=excluded.last_model,
            updated_at=CURRENT_TIMESTAMP
        """,
        (provider, model),
    )
    conn.commit()


def upsert_verified_model(conn: sqlite3.Connection, provider: str, model: str, ok: bool) -> None:
    ensure_chat_tables(conn)
    conn.execute(
        """
        INSERT INTO chat_verified_models (provider, model, verified_ok, last_verified_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(provider, model) DO UPDATE SET
            verified_ok=excluded.verified_ok,
            last_verified_at=CURRENT_TIMESTAMP
        """,
        (provider, model, 1 if ok else 0),
    )
    conn.commit()


def get_verified_models(conn: sqlite3.Connection, provider: Optional[str] = None) -> List[Dict[str, str]]:
    ensure_chat_tables(conn)
    if provider:
        rows = conn.execute(
            """
            SELECT provider, model
            FROM chat_verified_models
            WHERE verified_ok = 1 AND provider = ?
            ORDER BY last_verified_at DESC
            """,
            (provider,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT provider, model
            FROM chat_verified_models
            WHERE verified_ok = 1
            ORDER BY last_verified_at DESC
            """
        ).fetchall()
    return [{"provider": r[0], "model": r[1]} for r in rows]

