"""Debug similarity scores with known good matches."""
import numpy as np
from embeddings_onnx import OfflineEmbedder
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "storyvectordb" / "src"))
from sqlite_vectordb import SQLiteVectorDB
import json

embedder = OfflineEmbedder.load()
vectordb = SQLiteVectorDB('conversations_vectordb.db')

# Test with queries that SHOULD match
test_cases = [
    ("database migration", "Database Migration Planning"),
    ("API design", "API Design Review for Client Integration"),
    ("marketing campaign", "Marketing Campaign Strategy Discussion"),
    ("product roadmap", "Q4 Product Roadmap Planning"),
]

print("="*70)
print("Testing Similarity Scores for Known Matches")
print("="*70)

for query, expected_title in test_cases:
    print(f"\nQuery: '{query}'")
    print(f"Expected match: {expected_title}")
    print("-"*70)
    
    query_emb = embedder.embed_single(query)
    
    # Search
    results = vectordb.search_fast(query_emb.tolist(), top_n=5)
    
    # Find the expected match
    found_match = False
    for i, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        title = metadata.get('title', '')
        similarity = result['similarity']
        
        if expected_title.lower() in title.lower():
            found_match = True
            print(f"  [MATCH #{i}] {title}")
            print(f"    Similarity: {similarity:.6f}")
            print(f"    Type: {metadata.get('type', 'unknown')}")
            
            # Check if it's the top result
            if i == 1:
                print(f"    [TOP RESULT]")
            else:
                print(f"    [WARNING] Not top result (rank #{i})")
        else:
            if i <= 3:  # Show top 3 non-matches
                print(f"  [Result #{i}] {title[:50]}... (similarity: {similarity:.6f})")
    
    if not found_match:
        print(f"  [WARNING] Expected match not found in top 5 results!")

# Test with identical/similar text
print("\n" + "="*70)
print("Testing with Identical Text")
print("="*70)

# Get a stored vector and its content
with vectordb._get_connection() as conn:
    cursor = conn.execute("""
        SELECT vector, content, metadata 
        FROM vectors 
        WHERE json_extract(metadata, '$.title') LIKE '%Database%'
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        stored_vec = np.array(json.loads(row[0]))
        content = row[1]
        metadata = json.loads(row[2]) if row[2] else {}
        
        print(f"\nStored content: {content[:200]}...")
        print(f"Title: {metadata.get('title', 'N/A')}")
        
        # Embed the same content
        same_emb = embedder.embed_single(content)
        same_sim = float(np.dot(stored_vec, same_emb))
        print(f"\nSimilarity (stored vs re-embedded same text): {same_sim:.6f}")
        
        # Test with a relevant query
        query = "migrating from MySQL to PostgreSQL"
        query_emb = embedder.embed_single(query)
        query_sim = float(np.dot(stored_vec, query_emb))
        print(f"Similarity (stored vs 'migrating from MySQL to PostgreSQL'): {query_sim:.6f}")

