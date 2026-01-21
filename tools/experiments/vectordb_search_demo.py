"""
Manual debug script: vector DB search demo.

This is NOT a pytest test. Run manually:
  python tools/experiments/vectordb_search_demo.py
"""

from backend.vectordb.sqlite_vectordb import SQLiteVectorDB
from backend.vectordb.service import get_vectordb_path
from embeddings_onnx import OfflineEmbedder


def main() -> None:
    print("=" * 70)
    print("Vector Database Search Demo")
    print("=" * 70)

    vectordb_path = get_vectordb_path()
    print(f"VectorDB: {vectordb_path}")

    embedder = OfflineEmbedder.load()
    vectordb = SQLiteVectorDB(str(vectordb_path))
    stats = vectordb.get_stats()
    print(f"Total vectors: {stats['total_vectors']}")
    print(f"Unique files: {stats['unique_files']}")

    query = input("\nQuery: ").strip()
    if not query:
        return

    qemb = embedder.embed_single(query)
    results = vectordb.search_fast(qemb.tolist(), top_n=10, filters={"type": "chunk"})
    print(f"\nTop results for: {query!r}")
    for i, r in enumerate(results, 1):
        md = r.metadata or {}
        title = (md.get("title") or "Untitled")[:80]
        sim = r.similarity
        preview = (r.content or "").replace("\n", " ")[:160]
        print(f"{i:>2}. sim={sim:.3f} | {title} | {preview}")


if __name__ == "__main__":
    main()

