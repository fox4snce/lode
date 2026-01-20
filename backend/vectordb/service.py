"""
VectorDB service layer for Lode.

Provides:
- vectordb path resolution (packaging-safe via backend.db.get_data_dir())
- embedder loading (default: OfflineEmbedder)
- phrase search returning chunk-like results with source metadata
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from backend.vectordb.sqlite_vectordb import SQLiteVectorDB


def get_vectordb_path() -> Path:
    # Late import so tests can patch backend.db.get_data_dir more easily.
    from backend import db as backend_db

    return backend_db.get_data_dir() / "conversations_vectordb.db"


@lru_cache(maxsize=4)
def _get_vectordb(db_path_str: str) -> SQLiteVectorDB:
    return SQLiteVectorDB(db_path_str)


def get_vectordb() -> SQLiteVectorDB:
    p = get_vectordb_path()
    return _get_vectordb(str(p))


@lru_cache(maxsize=1)
def get_embedder():
    # Default embedder: BGE-small-en-v1.5 (better quality than MiniLM)
    # TODO: Add user-configurable embedding provider support
    from embeddings_onnx import OfflineEmbedder

    return OfflineEmbedder.load(model_dir="vendor/embedder_bge_small_v1_5")


def _ensure_2d(a: np.ndarray) -> np.ndarray:
    if a.ndim == 1:
        return a.reshape(1, -1)
    return a


def search_phrases(
    *,
    phrases: List[str],
    top_k: int = 5,
    min_similarity: Optional[float] = None,
    filters: Optional[Dict[str, Any]] = None,
    include_content: bool = True,
    include_debug: bool = False,
) -> List[Dict[str, Any]]:
    """
    Search the vectordb for each phrase and return results grouped by phrase.
    """
    if not phrases:
        return []

    embedder = get_embedder()
    vectordb = get_vectordb()

    # Embed all phrases (batch)
    embs = embedder.embed(phrases)
    embs = _ensure_2d(np.asarray(embs, dtype=np.float32))

    out: List[Dict[str, Any]] = []
    for phrase, emb in zip(phrases, embs):
        # Pull more candidates than requested so we can do "best per conversation" (reduces noisy spammy results)
        candidate_k = min(max(top_k * 20, top_k), 500)
        rows = vectordb.search_fast(emb.tolist(), top_n=candidate_k, filters=filters)

        # Best-per-conversation selection
        best_by_conv: Dict[str, Any] = {}
        for r in rows:
            md = r.metadata or {}
            conv_id = md.get("conversation_id") or r.file_id or ""

            # Optional: skip tiny chunks if we have word_count metadata
            wc = md.get("chunk_word_count")
            if isinstance(wc, int) and wc > 0 and wc < 30:
                continue

            prev = best_by_conv.get(conv_id)
            if prev is None or r.similarity > prev.similarity:
                best_by_conv[conv_id] = r

        # Order by similarity and take top_k
        picked = sorted(best_by_conv.values(), key=lambda x: x.similarity, reverse=True)[:top_k]

        results: List[Dict[str, Any]] = []
        seen_keys = set()
        for r in picked:
            if min_similarity is not None and r.similarity < float(min_similarity):
                continue

            md = r.metadata or {}
            dedupe_key = (md.get("conversation_id"), md.get("chunk_index"), md.get("type"), r.content)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            source = {
                "conversation_id": md.get("conversation_id"),
                "message_ids": md.get("message_ids"),
                "chunk_index": md.get("chunk_index"),
                "vectordb_row_id": r.id,
            }

            item: Dict[str, Any] = {"similarity": r.similarity, "source": source}
            if include_content:
                item["content"] = r.content
            item["metadata"] = md
            if include_debug:
                item["file_id"] = r.file_id
            results.append(item)

        out.append({"phrase": phrase, "results": results})

    return out


def get_status() -> Dict[str, Any]:
    path = get_vectordb_path()
    exists = path.exists() and path.is_file()
    status: Dict[str, Any] = {
        "vectordb_exists": exists,
        "vectordb_path": str(path),
    }
    if exists:
        stats = get_vectordb().get_stats()
        status["stats"] = stats
    return status

