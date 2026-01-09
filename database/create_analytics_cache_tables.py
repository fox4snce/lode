"""
Create tables for caching analytics results.

Goal:
- Analytics are computed once and stored in SQLite.
- UI pages read cached results (fast, stable).
- Cache is only refreshed when the user explicitly triggers refresh.
"""

import sqlite3


def create_analytics_cache_tables(db_path: str = "conversations.db") -> None:
    """Create analytics cache table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_cache (
            cache_key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_analytics_cache_updated_at ON analytics_cache(updated_at)"
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_analytics_cache_tables()

