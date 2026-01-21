"""
Meaningful API-level tests for VectorDB search.

These tests:
- build a real SQLite vectordb (tiny, temporary)
- insert chunk rows with realistic source metadata (conversation_id + message_ids)
- patch the backend's embedder to a deterministic fake
- hit the FastAPI endpoints via TestClient and assert behavior
"""

import sys
import math
import tempfile
import unittest
import warnings
import os
from pathlib import Path
from typing import List
from unittest.mock import patch

import numpy as np

# Ensure project root is on sys.path when tests are executed as scripts.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def _unit(vec: List[float]) -> List[float]:
    v = np.array(vec, dtype=np.float32)
    n = float(np.linalg.norm(v)) + 1e-12
    v = v / n
    return v.tolist()


class FakeEmbedder:
    """
    Deterministic embedder for tests.
    Produces a 3-dim unit vector based on simple keyword buckets.
    """

    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        out = []
        for t in texts:
            tl = (t or "").lower()
            if "alpha" in tl:
                out.append(_unit([1.0, 0.0, 0.0]))
            elif "beta" in tl:
                out.append(_unit([0.0, 1.0, 0.0]))
            else:
                out.append(_unit([0.0, 0.0, 1.0]))
        return np.array(out, dtype=np.float32)


class TestVectorDBAPI(unittest.TestCase):
    def setUp(self):
        # Windows + sqlite + background threads can transiently hold file handles.
        # Ignore cleanup errors so tests still fail/pass based on assertions, not temp file locks.
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.data_dir = Path(self.tmp.name)
        self.vectordb_path = self.data_dir / "conversations_vectordb.db"

        # Create a real vectordb and insert realistic chunk rows
        from backend.vectordb.sqlite_vectordb import SQLiteVectorDB

        db = SQLiteVectorDB(self.vectordb_path)
        db.insert(
            content="alpha chunk about databases",
            vector=_unit([1.0, 0.0, 0.0]),
            metadata={
                "type": "chunk",
                "conversation_id": "conv_alpha",
                "message_ids": ["m1", "m2"],
                "chunk_index": 0,
                "ai_source": "gpt",
            },
            file_id="conv_alpha",
        )
        db.insert(
            content="beta chunk about embeddings",
            vector=_unit([0.0, 1.0, 0.0]),
            metadata={
                "type": "chunk",
                "conversation_id": "conv_beta",
                "message_ids": ["m10", "m11", "m12"],
                "chunk_index": 1,
                "ai_source": "claude",
            },
            file_id="conv_beta",
        )
        db.insert(
            content="neutral chunk about something else",
            vector=_unit([0.0, 0.0, 1.0]),
            metadata={
                "type": "chunk",
                "conversation_id": "conv_neutral",
                "message_ids": ["m99"],
                "chunk_index": 2,
                "ai_source": "gpt",
            },
            file_id="conv_neutral",
        )

        # Ensure the VectorDB API router is registered (Pro-only feature).
        # We must set env var BEFORE importing backend.main, because router inclusion happens at import time.
        os.environ["LODE_BUILD_TYPE"] = "pro"
        for mod in ("backend.main", "backend.feature_flags"):
            if mod in sys.modules:
                del sys.modules[mod]

        # Import app after data is set up
        from backend.main import app
        from fastapi.testclient import TestClient

        warnings.filterwarnings("ignore", category=DeprecationWarning)
        self.client = TestClient(app)

        # Patch service to use our temp vectordb + fake embedder
        self.patches = [
            patch("backend.vectordb.service.get_vectordb_path", return_value=self.vectordb_path),
            patch("backend.vectordb.service.get_embedder", return_value=FakeEmbedder()),
        ]
        for p in self.patches:
            p.start()

        # Ensure the cached vectordb is reset for this path
        from backend.vectordb import service as svc
        svc._get_vectordb.cache_clear()

    def tearDown(self):
        try:
            self.client.close()
        except Exception:
            pass

        for p in self.patches:
            p.stop()

        # Ensure cached vectordb instances are released before deleting temp files (Windows).
        try:
            from backend.vectordb import service as svc
            svc._get_vectordb.cache_clear()
        except Exception:
            pass

        self.tmp.cleanup()

    def test_status_reports_existing_db_and_stats(self):
        r = self.client.get("/api/vectordb/status")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertTrue(data["vectordb_exists"])
        self.assertIn("stats", data)
        self.assertEqual(data["stats"]["total_vectors"], 3)

    def test_search_returns_chunks_with_sources(self):
        r = self.client.post(
            "/api/vectordb/search",
            json={
                "phrases": ["alpha", "beta"],
                "top_k": 2,
                "filters": {"type": "chunk"},
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        results_by_phrase = body["results_by_phrase"]
        self.assertEqual(len(results_by_phrase), 2)

        alpha = results_by_phrase[0]
        self.assertEqual(alpha["phrase"], "alpha")
        self.assertGreaterEqual(len(alpha["results"]), 1)
        best_alpha = alpha["results"][0]
        self.assertIn("similarity", best_alpha)
        self.assertIn("content", best_alpha)
        self.assertIn("source", best_alpha)
        self.assertEqual(best_alpha["source"]["conversation_id"], "conv_alpha")
        self.assertEqual(best_alpha["source"]["message_ids"], ["m1", "m2"])
        self.assertEqual(best_alpha["source"]["chunk_index"], 0)
        self.assertTrue(best_alpha["similarity"] > 0.9)

        beta = results_by_phrase[1]
        self.assertEqual(beta["phrase"], "beta")
        best_beta = beta["results"][0]
        self.assertEqual(best_beta["source"]["conversation_id"], "conv_beta")
        self.assertEqual(best_beta["source"]["message_ids"], ["m10", "m11", "m12"])
        self.assertTrue(best_beta["similarity"] > 0.9)

    def test_filters_and_min_similarity_work(self):
        # Filter to GPT only, query for beta -> should not return conv_beta (claude)
        r = self.client.post(
            "/api/vectordb/search",
            json={"phrases": ["beta"], "top_k": 5, "filters": {"type": "chunk", "ai_source": "gpt"}},
        )
        self.assertEqual(r.status_code, 200, r.text)
        results = r.json()["results_by_phrase"][0]["results"]
        self.assertTrue(all(res["metadata"].get("ai_source") == "gpt" for res in results))

        # min_similarity should drop weak matches
        r2 = self.client.post(
            "/api/vectordb/search",
            json={"phrases": ["alpha"], "top_k": 3, "filters": {"type": "chunk"}, "min_similarity": 0.999},
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        results2 = r2.json()["results_by_phrase"][0]["results"]
        self.assertGreaterEqual(len(results2), 1)
        self.assertTrue(all(res["similarity"] >= 0.999 for res in results2))

    def test_include_content_false_omits_content(self):
        r = self.client.post(
            "/api/vectordb/search",
            json={"phrases": ["alpha"], "top_k": 1, "filters": {"type": "chunk"}, "include_content": False},
        )
        self.assertEqual(r.status_code, 200, r.text)
        res = r.json()["results_by_phrase"][0]["results"][0]
        self.assertNotIn("content", res)


if __name__ == "__main__":
    unittest.main()

