"""
Manual debug script: compare conversation-level vs chunk-level search.

Run:
  python tools/experiments/full_vs_chunks.py
"""

from embeddings_onnx import OfflineEmbedder

from backend.vectordb.sqlite_vectordb import SQLiteVectorDB
from backend.vectordb.service import get_vectordb_path


def main() -> None:
    embedder = OfflineEmbedder.load()
    vectordb = SQLiteVectorDB(str(get_vectordb_path()))

    query = "database migration"
    query_emb = embedder.embed_single(query)

    print("=" * 70)
    print(f"Query: {query!r}")
    print("=" * 70)

    print("\n[Chunks Only]")
    results_chunks = vectordb.search_fast(query_emb.tolist(), top_n=5, filters={"type": "chunk"})
    for i, r in enumerate(results_chunks, 1):
        meta = r.metadata or {}
        print(f"  {i}. {str(meta.get('title','N/A'))[:50]}... (sim: {r.similarity:.4f})")

    print("\n[Conversation Only]")
    results_conv = vectordb.search_fast(query_emb.tolist(), top_n=5, filters={"type": "conversation"})
    for i, r in enumerate(results_conv, 1):
        meta = r.metadata or {}
        print(f"  {i}. {str(meta.get('title','N/A'))[:50]}... (sim: {r.similarity:.4f})")


if __name__ == "__main__":
    main()

