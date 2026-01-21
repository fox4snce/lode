"""
Manual debug script: inspect similarity scores for a few queries.

Run:
  python tools/experiments/similarity_debug.py
"""

from embeddings_onnx import OfflineEmbedder

from backend.vectordb.sqlite_vectordb import SQLiteVectorDB
from backend.vectordb.service import get_vectordb_path


def main() -> None:
    embedder = OfflineEmbedder.load()
    vectordb = SQLiteVectorDB(str(get_vectordb_path()))

    test_cases = [
        "database migration",
        "API design",
        "marketing campaign",
        "product roadmap",
    ]

    print("=" * 70)
    print("Similarity Debug")
    print("=" * 70)

    for query in test_cases:
        print(f"\nQuery: {query!r}")
        q = embedder.embed_single(query)
        results = vectordb.search_fast(q.tolist(), top_n=5, filters={"type": "chunk"})
        for i, r in enumerate(results, 1):
            md = r.metadata or {}
            title = (md.get("title") or "Untitled")[:60]
            print(f"  {i}. sim={r.similarity:.4f} | {title}")


if __name__ == "__main__":
    main()

