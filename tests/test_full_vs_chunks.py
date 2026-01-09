"""Compare full conversation vs chunk search results."""
import numpy as np
from embeddings_onnx import OfflineEmbedder
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "storyvectordb" / "src"))
from sqlite_vectordb import SQLiteVectorDB

embedder = OfflineEmbedder.load()
vectordb = SQLiteVectorDB('conversations_vectordb.db')

query = "database migration"
query_emb = embedder.embed_single(query)

print("="*70)
print(f"Query: '{query}'")
print("="*70)

# Search all
print("\n[All Results]")
results_all = vectordb.search_fast(query_emb.tolist(), top_n=10)
for i, r in enumerate(results_all[:5], 1):
    meta = r.get('metadata', {})
    print(f"  {i}. {meta.get('title', 'N/A')[:50]}... (sim: {r['similarity']:.4f}, type: {meta.get('type', '?')})")

# Search only full conversations
print("\n[Full Conversations Only]")
results_full = vectordb.search_fast(query_emb.tolist(), top_n=5, filters={'type': 'full'})
for i, r in enumerate(results_full, 1):
    meta = r.get('metadata', {})
    print(f"  {i}. {meta.get('title', 'N/A')[:50]}... (sim: {r['similarity']:.4f})")

# Search only chunks
print("\n[Chunks Only]")
results_chunks = vectordb.search_fast(query_emb.tolist(), top_n=5, filters={'type': 'chunk'})
for i, r in enumerate(results_chunks, 1):
    meta = r.get('metadata', {})
    print(f"  {i}. {meta.get('title', 'N/A')[:50]}... (sim: {r['similarity']:.4f})")

# The issue: full conversations have low scores because they contain many topics
# Solution: We might need to use a different approach for full conversations
# Option 1: Use max similarity from chunks per conversation
# Option 2: Use a different embedding strategy for full conversations
# Option 3: Use hybrid search (combine full + best chunk per conversation)

print("\n" + "="*70)
print("Analysis:")
print("="*70)
print("Full conversations have lower scores because:")
print("  1. They contain multiple topics mixed together")
print("  2. A specific query only matches part of the conversation")
print("  3. The embedding averages out all topics")
print("\nSolutions:")
print("  1. Use chunk-based search (already working well)")
print("  2. Use hybrid search: combine full + best chunk per conversation")
print("  3. Use conversation summaries instead of full text")

