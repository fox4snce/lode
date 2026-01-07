"""
Improved vector database search with better similarity scores.

Uses hybrid approach:
1. Prefer summaries if available (more focused)
2. Use chunks grouped by conversation
3. Fall back to full conversations
"""
import numpy as np
from embeddings_onnx import OfflineEmbedder
import sys
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "storyvectordb" / "src"))
from sqlite_vectordb import SQLiteVectorDB


def hybrid_search(
    vectordb: SQLiteVectorDB,
    query_embedding: np.ndarray,
    top_n: int = 5,
    prefer_summaries: bool = True,
    use_chunks: bool = True
) -> List[Dict]:
    """
    Hybrid search that groups results by conversation and uses best match per conversation.
    
    Strategy:
    1. Search summaries first (if available and prefer_summaries=True)
    2. Search chunks and group by conversation, taking best chunk per conversation
    3. Combine and deduplicate, prioritizing summaries
    """
    results = []
    seen_conversations = set()
    
    # 1. Search summaries first (most focused)
    if prefer_summaries:
        summary_results = vectordb.search_fast(
            query_embedding.tolist(),
            top_n=top_n * 2,  # Get more to filter
            filters={'type': 'summary'}
        )
        
        for result in summary_results:
            conv_id = result.get('metadata', {}).get('conversation_id')
            if conv_id and conv_id not in seen_conversations:
                seen_conversations.add(conv_id)
                results.append({
                    **result,
                    'match_type': 'summary'
                })
                if len(results) >= top_n:
                    break
    
    # 2. Search chunks and group by conversation
    if use_chunks and len(results) < top_n:
        chunk_results = vectordb.search_fast(
            query_embedding.tolist(),
            top_n=top_n * 5,  # Get many chunks
            filters={'type': 'chunk'}
        )
        
        # Group by conversation, keep best chunk per conversation
        chunks_by_conv = defaultdict(list)
        for chunk in chunk_results:
            conv_id = chunk.get('metadata', {}).get('conversation_id')
            if conv_id:
                chunks_by_conv[conv_id].append(chunk)
        
        # Add best chunk per conversation (if not already seen)
        for conv_id, chunks in chunks_by_conv.items():
            if conv_id not in seen_conversations:
                # Sort by similarity and take best
                best_chunk = max(chunks, key=lambda x: x['similarity'])
                seen_conversations.add(conv_id)
                results.append({
                    **best_chunk,
                    'match_type': 'chunk',
                    'chunk_count': len(chunks)  # How many chunks matched
                })
                if len(results) >= top_n:
                    break
    
    # 3. Fill remaining with full conversations (if needed)
    if len(results) < top_n:
        full_results = vectordb.search_fast(
            query_embedding.tolist(),
            top_n=top_n - len(results),
            filters={'type': 'full'}
        )
        
        for result in full_results:
            conv_id = result.get('metadata', {}).get('conversation_id')
            if conv_id and conv_id not in seen_conversations:
                seen_conversations.add(conv_id)
                results.append({
                    **result,
                    'match_type': 'full'
                })
                if len(results) >= top_n:
                    break
    
    # Sort by similarity (descending)
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_n]


def search_conversations(
    query: str,
    vectordb_path: str = 'conversations_vectordb.db',
    top_n: int = 5
) -> List[Dict]:
    """
    Search conversations with improved similarity scores.
    
    Args:
        query: Search query text
        vectordb_path: Path to vector database
        top_n: Number of results to return
    
    Returns:
        List of search results with improved similarity scores
    """
    # Load embedder
    embedder = OfflineEmbedder.load()
    
    # Load vectordb
    vectordb = SQLiteVectorDB(vectordb_path)
    
    # Embed query
    query_embedding = embedder.embed_single(query)
    
    # Hybrid search
    results = hybrid_search(vectordb, query_embedding, top_n=top_n)
    
    return results


if __name__ == "__main__":
    import sys
    
    query = sys.argv[1] if len(sys.argv) > 1 else "database migration"
    
    print("="*70)
    print(f"Improved Search: '{query}'")
    print("="*70)
    
    results = search_conversations(query, top_n=5)
    
    for i, result in enumerate(results, 1):
        similarity = result['similarity']
        metadata = result.get('metadata', {})
        match_type = result.get('match_type', 'unknown')
        title = metadata.get('title', '(no title)')
        conv_id = metadata.get('conversation_id', 'unknown')
        content = result.get('content', '')[:150]
        
        print(f"\n[{i}] {title}")
        print(f"    Similarity: {similarity:.4f}")
        print(f"    Match type: {match_type}")
        print(f"    Conversation: {conv_id[:40]}...")
        print(f"    Content: {content}...")
        
        if match_type == 'chunk' and 'chunk_count' in result:
            print(f"    Matched chunks: {result['chunk_count']}")

