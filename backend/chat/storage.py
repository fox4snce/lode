"""
SQLite-backed persistence for chat UI state.

We store this in the main Lode database (conversations.db) because:
- it's already initialized before Chat can be accessed
- it's per-user persistent state
"""

from __future__ import annotations

import sqlite3
import json
from typing import Any, Dict, List, Optional


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, spec: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {spec}")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise


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
    # Migrate: add UI settings columns if missing
    _add_column_if_missing(conn, "chat_user_settings", "context_window_size", "INTEGER")
    _add_column_if_missing(conn, "chat_user_settings", "min_similarity", "REAL")
    _add_column_if_missing(conn, "chat_user_settings", "max_context_chunks", "INTEGER")
    _add_column_if_missing(conn, "chat_user_settings", "show_debug", "INTEGER")
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_conversation_history (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            history_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


# Defaults for UI settings when not set in DB
DEFAULT_CONTEXT_WINDOW = 4000
DEFAULT_MIN_SIMILARITY = 0.5
DEFAULT_MAX_CONTEXT_CHUNKS = 5
DEFAULT_SHOW_DEBUG = 0


def get_settings(conn: sqlite3.Connection) -> Dict[str, Any]:
    ensure_chat_tables(conn)
    row = conn.execute(
        """SELECT last_provider, last_model, context_window_size, min_similarity,
                  max_context_chunks, show_debug
           FROM chat_user_settings WHERE id = 1"""
    ).fetchone()
    if not row:
        return {
            "last_provider": None,
            "last_model": None,
            "context_window_size": DEFAULT_CONTEXT_WINDOW,
            "min_similarity": DEFAULT_MIN_SIMILARITY,
            "max_context_chunks": DEFAULT_MAX_CONTEXT_CHUNKS,
            "show_debug": DEFAULT_SHOW_DEBUG,
        }
    ctx = row[2] if row[2] is not None else DEFAULT_CONTEXT_WINDOW
    ctx = max(1, min(100_000, ctx))
    return {
        "last_provider": row[0],
        "last_model": row[1],
        "context_window_size": ctx,
        "min_similarity": float(row[3]) if row[3] is not None else DEFAULT_MIN_SIMILARITY,
        "max_context_chunks": row[4] if row[4] is not None else DEFAULT_MAX_CONTEXT_CHUNKS,
        "show_debug": 1 if row[5] else 0,
    }


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


def set_ui_settings(
    conn: sqlite3.Connection,
    *,
    context_window_size: Optional[int] = None,
    min_similarity: Optional[float] = None,
    max_context_chunks: Optional[int] = None,
    show_debug: Optional[bool] = None,
) -> None:
    """Persist chat UI settings. Only provided keys are updated."""
    ensure_chat_tables(conn)
    # Ensure row exists
    conn.execute(
        """
        INSERT INTO chat_user_settings (id, last_provider, last_model, updated_at)
        VALUES (1, NULL, NULL, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO NOTHING
        """
    )
    updates: List[str] = ["updated_at = CURRENT_TIMESTAMP"]
    args: List[Any] = []
    if context_window_size is not None:
        updates.append("context_window_size = ?")
        args.append(context_window_size)
    if min_similarity is not None:
        updates.append("min_similarity = ?")
        args.append(min_similarity)
    if max_context_chunks is not None:
        updates.append("max_context_chunks = ?")
        args.append(max_context_chunks)
    if show_debug is not None:
        updates.append("show_debug = ?")
        args.append(1 if show_debug else 0)
    if len(args) == 0:
        return
    args.append(1)
    conn.execute(
        f"UPDATE chat_user_settings SET {', '.join(updates)} WHERE id = ?",
        tuple(args),
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


def save_chat_history(conn: sqlite3.Connection, history: List[Dict[str, str]]) -> None:
    """Save chat conversation history."""
    ensure_chat_tables(conn)
    history_json = json.dumps(history)
    conn.execute(
        """
        INSERT INTO chat_conversation_history (id, history_json, updated_at)
        VALUES (1, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            history_json=excluded.history_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (history_json,),
    )
    conn.commit()


def load_chat_history(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    """Load chat conversation history."""
    ensure_chat_tables(conn)
    row = conn.execute(
        "SELECT history_json FROM chat_conversation_history WHERE id = 1"
    ).fetchone()
    if not row or not row[0]:
        return []
    try:
        return json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return []


def clear_chat_history(conn: sqlite3.Connection) -> None:
    """Clear chat conversation history."""
    ensure_chat_tables(conn)
    conn.execute("DELETE FROM chat_conversation_history WHERE id = 1")
    conn.commit()

