"""
SQLite-backed VectorDB used by Lode.

This is a small, self-contained implementation intended to replace runtime `sys.path`
imports from the separate `storyvectordb/` repo.

Notes:
- Vectors are stored as JSON arrays of floats.
- Similarity is cosine similarity, implemented as a dot product assuming vectors are L2-normalized.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class VectorRow:
    id: int
    content: str
    vector: List[float]
    metadata: Optional[Dict[str, Any]]
    file_id: Optional[str]
    similarity: float


class SQLiteVectorDB:
    """A lightweight vector database implemented on top of SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._initialize_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # performance knobs (safe defaults)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA temp_store=MEMORY;")
        except Exception:
            pass
        return conn

    def _initialize_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    vector TEXT NOT NULL,   -- JSON array of floats
                    metadata TEXT,          -- JSON object (nullable)
                    file_id TEXT,           -- optional grouping key
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_file_id ON vectors(file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_created_at ON vectors(created_at)")
            
            # Check if unique index already exists
            index_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_vectors_file_id_unique'"
            ).fetchone()
            
            if not index_exists:
                # Clean up duplicates before creating unique index
                # Keep the most recent row per file_id (highest id, which is auto-increment)
                conn.execute("""
                    DELETE FROM vectors
                    WHERE id NOT IN (
                        SELECT MAX(id)
                        FROM vectors
                        WHERE file_id IS NOT NULL
                        GROUP BY file_id
                    )
                    AND file_id IS NOT NULL
                """)
                # Ensure idempotent upserts by file_id (NULLs are allowed multiple times in UNIQUE)
                conn.execute("CREATE UNIQUE INDEX idx_vectors_file_id_unique ON vectors(file_id)")

    def insert(
        self,
        *,
        content: str,
        vector: Sequence[float],
        metadata: Optional[Dict[str, Any]] = None,
        file_id: Optional[str] = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                # REPLACE is safe due to UNIQUE(file_id); re-index runs won't create duplicates.
                "INSERT OR REPLACE INTO vectors (content, vector, metadata, file_id) VALUES (?, ?, ?, ?)",
                (content, json.dumps(list(vector)), json.dumps(metadata) if metadata is not None else None, file_id),
            )
            return int(cur.lastrowid)

    def insert_batch(self, items: List[Dict[str, Any]]) -> List[int]:
        ids: List[int] = []
        if not items:
            return ids
        
        # For very large batches, process in smaller chunks to avoid timeouts/locks
        chunk_size = 100
        if len(items) > chunk_size:
            all_ids = []
            for i in range(0, len(items), chunk_size):
                chunk = items[i:i + chunk_size]
                all_ids.extend(self.insert_batch(chunk))
            return all_ids
        
        with self._connect() as conn:
            cur = conn.cursor()
            conn.execute("BEGIN")
            try:
                for item in items:
                    cur.execute(
                        "INSERT OR REPLACE INTO vectors (content, vector, metadata, file_id) VALUES (?, ?, ?, ?)",
                        (
                            item["content"],
                            json.dumps(list(item["vector"])),
                            json.dumps(item.get("metadata")) if item.get("metadata") is not None else None,
                            item.get("file_id"),
                        ),
                    )
                    ids.append(int(cur.lastrowid))
                conn.execute("COMMIT")
            except Exception as e:
                conn.execute("ROLLBACK")
                # Re-raise with more context
                raise Exception(f"Batch insert failed for {len(items)} items: {e}") from e
        return ids

    def get_stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            total = int(conn.execute("SELECT COUNT(*) AS c FROM vectors").fetchone()["c"])
            unique_files = int(
                conn.execute("SELECT COUNT(DISTINCT file_id) AS c FROM vectors WHERE file_id IS NOT NULL").fetchone()[
                    "c"
                ]
            )
        return {"total_vectors": total, "unique_files": unique_files}

    def search_fast(
        self,
        query_vector: Sequence[float],
        *,
        top_n: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorRow]:
        """
        Compute similarities in a thin Python loop (faster than SQL UDF ordering for small-medium sets).
        Expects stored vectors and query_vector to be L2-normalized so cosine similarity == dot product.
        """
        q = np.array(query_vector, dtype=np.float32)
        if q.ndim != 1:
            raise ValueError("query_vector must be 1D")

        # Normalize defensively (so callers don't have to)
        q_norm = float(np.linalg.norm(q)) + 1e-12
        q = q / q_norm

        where = ""
        params: List[Any] = []
        if filters:
            conditions = []
            for k, v in filters.items():
                conditions.append(f"json_extract(metadata, '$.{k}') = ?")
                params.append(v)
            where = "WHERE " + " AND ".join(conditions)

        rows: List[VectorRow] = []
        with self._connect() as conn:
            cur = conn.execute(f"SELECT id, content, vector, metadata, file_id FROM vectors {where}", params)
            for r in cur.fetchall():
                vec = np.array(json.loads(r["vector"]), dtype=np.float32)
                v_norm = float(np.linalg.norm(vec)) + 1e-12
                vec = vec / v_norm
                sim = float(np.dot(q, vec))
                rows.append(
                    VectorRow(
                        id=int(r["id"]),
                        content=str(r["content"]),
                        vector=json.loads(r["vector"]),
                        metadata=json.loads(r["metadata"]) if r["metadata"] else None,
                        file_id=r["file_id"],
                        similarity=sim,
                    )
                )

        rows.sort(key=lambda x: x.similarity, reverse=True)
        return rows[: max(0, int(top_n))]

