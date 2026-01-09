"""
Test vector database search and retrieval functionality.

Tests semantic search using ONNX embeddings.
"""
import sys
from pathlib import Path

# Add storyvectordb to path
sys.path.insert(0, str(Path(__file__).parent / "storyvectordb" / "src"))
from sqlite_vectordb import SQLiteVectorDB

from embeddings_onnx import OfflineEmbedder

VECTORDB_PATH = 'conversations_vectordb.db'


def test_search():
    """Test semantic search in vector database."""
    print("="*70)
    print("Vector Database Search Test")
    print("="*70)
    
    # Load embedder
    print("\n[1/3] Loading ONNX embedder...")
    try:
        embedder = OfflineEmbedder.load()
        print("  [SUCCESS] Embedder loaded")
    except Exception as e:
        print(f"  [ERROR] Failed to load embedder: {e}")
        return
    
    # Load vectordb
    print("\n[2/3] Loading vector database...")
    try:
        vectordb = SQLiteVectorDB(VECTORDB_PATH)
        stats = vectordb.get_stats()
        print(f"  [SUCCESS] Vector DB loaded")
        print(f"  Total vectors: {stats['total_vectors']}")
        print(f"  Unique files: {stats['unique_files']}")
        
        if stats['total_vectors'] == 0:
            print("\n  [WARNING] Vector database is empty!")
            print("  Run build_vectordb.py first to populate it.")
            return
    except Exception as e:
        print(f"  [ERROR] Failed to load vector DB: {e}")
        return
    
    # Test queries
    print("\n[3/3] Testing search queries...")
    print("-"*70)
    
    test_queries = [
        "database migration",
        "product roadmap planning",
        "API design",
        "team meeting",
        "client integration",
        "marketing campaign",
        "technical architecture",
    ]
    
    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        print("-"*70)
        
        # Embed query
        query_embedding = embedder.embed_single(query)
        
        # Search
        results = vectordb.search_fast(query_embedding.tolist(), top_n=5)
        
        if results:
            for i, result in enumerate(results, 1):
                similarity = result['similarity']
                content = result['content']
                metadata = result.get('metadata', {})
                conv_id = metadata.get('conversation_id', 'unknown')
                title = metadata.get('title', '(no title)')
                vec_type = metadata.get('type', 'unknown')
                
                # Truncate content for display
                content_preview = content[:150] + "..." if len(content) > 150 else content
                
                print(f"\n  [{i}] Similarity: {similarity:.4f}")
                print(f"      Conversation: {conv_id[:40]}...")
                print(f"      Title: {title}")
                print(f"      Type: {vec_type}")
                print(f"      Content: {content_preview}")
        else:
            print("  No results found")
    
    # Test with filters
    print("\n" + "="*70)
    print("Testing filtered search...")
    print("="*70)
    
    query = "database"
    query_embedding = embedder.embed_single(query)
    
    # Search with filter (e.g., only summaries)
    print(f"\nQuery: \"{query}\" (filtered to summaries only)")
    results = vectordb.search(
        query_embedding.tolist(),
        top_n=3,
        filters={'type': 'summary'}
    )
    
    if results:
        for i, result in enumerate(results, 1):
            similarity = result['similarity']
            metadata = result.get('metadata', {})
            title = metadata.get('title', '(no title)')
            print(f"\n  [{i}] {title} (similarity: {similarity:.4f})")
    else:
        print("  No results found")
    
    print("\n" + "="*70)
    print("[COMPLETE] Search tests finished")
    print("="*70)


if __name__ == "__main__":
    test_search()

