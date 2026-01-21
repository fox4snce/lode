"""
Manual debug script: check embedding/vector norms and similarity math.

Run:
  python tools/experiments/embedding_norms.py
"""

import json

import numpy as np

from backend.vectordb.sqlite_vectordb import SQLiteVectorDB
from backend.vectordb.service import get_vectordb_path
from embeddings_onnx import OfflineEmbedder


def main() -> None:
    embedder = OfflineEmbedder.load()
    vectordb = SQLiteVectorDB(str(get_vectordb_path()))

    query = "database migration"
    query_emb = embedder.embed_single(query)
    print(f"Query: {query!r}")
    print(f"Query embedding norm: {np.linalg.norm(query_emb):.6f}")
    print(f"Query embedding shape: {query_emb.shape}")
    print()

    # Grab one stored vector
    with vectordb._connect() as conn:
        row = conn.execute("SELECT vector, content FROM vectors LIMIT 1").fetchone()
        if not row:
            print("No vectors in DB.")
            return
        stored_vec = np.array(json.loads(row["vector"]), dtype=np.float32)
        content = row["content"]

    print(f"Stored vector norm: {np.linalg.norm(stored_vec):.6f}")
    print(f"Stored vector shape: {stored_vec.shape}")
    print(f"Content preview: {(content or '')[:120]}...")
    print()

    dot = float(np.dot(query_emb, stored_vec))
    manual_cosine = float(np.dot(query_emb, stored_vec) / ((np.linalg.norm(query_emb) + 1e-12) * (np.linalg.norm(stored_vec) + 1e-12)))
    print(f"Dot product: {dot:.6f}")
    print(f"Manual cosine: {manual_cosine:.6f}")


if __name__ == "__main__":
    main()

