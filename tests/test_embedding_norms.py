"""Test if embeddings are properly normalized."""
import numpy as np
from embeddings_onnx import OfflineEmbedder
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "storyvectordb" / "src"))
from sqlite_vectordb import SQLiteVectorDB
import json

embedder = OfflineEmbedder.load()
vectordb = SQLiteVectorDB('conversations_vectordb.db')

# Test query embedding
query = "database migration"
query_emb = embedder.embed_single(query)
print(f"Query: '{query}'")
print(f"Query embedding norm: {np.linalg.norm(query_emb):.6f}")
print(f"Query embedding shape: {query_emb.shape}")
print()

# Get a stored vector
with vectordb._get_connection() as conn:
    cursor = conn.execute("SELECT vector, content FROM vectors LIMIT 1")
    row = cursor.fetchone()
    if row:
        stored_vec = np.array(json.loads(row[0]))  # vector is first column
        content = row[1]  # content is second column
        print(f"Stored vector norm: {np.linalg.norm(stored_vec):.6f}")
        print(f"Stored vector shape: {stored_vec.shape}")
        print(f"Content preview: {content[:100]}...")
        print()
        
        # Compute similarity
        similarity = float(np.dot(query_emb, stored_vec))
        print(f"Dot product (similarity): {similarity:.6f}")
        
        # Manual cosine similarity
        norm1 = np.linalg.norm(query_emb)
        norm2 = np.linalg.norm(stored_vec)
        manual_cosine = float(np.dot(query_emb, stored_vec) / (norm1 * norm2))
        print(f"Manual cosine similarity: {manual_cosine:.6f}")
        print()
        
        # Test with same text
        same_emb = embedder.embed_single(content[:100])
        same_sim = float(np.dot(query_emb, same_emb))
        print(f"Similarity with same text (first 100 chars): {same_sim:.6f}")

