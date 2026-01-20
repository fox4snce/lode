"""
Benchmark current MiniLM-L6-v2 model: save queries, results, and timing.

This will be used for side-by-side comparison after upgrading to BGE-small.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from backend.vectordb.service import get_vectordb, get_embedder
from backend.vectordb.sqlite_vectordb import SQLiteVectorDB


def benchmark_query(
    query: str,
    embedder,
    vectordb: SQLiteVectorDB,
    top_k: int = 10,
) -> Dict:
    """Run a query and measure timing + collect results."""
    # Time embedding
    embed_start = time.perf_counter()
    query_emb = embedder.embed([query])[0]
    embed_time = time.perf_counter() - embed_start
    
    # Time search
    search_start = time.perf_counter()
    rows = vectordb.search_fast(query_emb.tolist(), top_n=top_k * 5, filters={'type': 'chunk'})
    search_time = time.perf_counter() - search_start
    
    # Best per conversation (like the real search does)
    best_by_conv: Dict[str, tuple] = {}
    for r in rows:
        md = r.metadata or {}
        conv_id = md.get("conversation_id") or r.file_id or ""
        prev = best_by_conv.get(conv_id)
        if prev is None or r.similarity > prev[0]:
            best_by_conv[conv_id] = (r.similarity, md, r.content[:300])
    
    # Sort and take top_k
    best_results = sorted(best_by_conv.values(), key=lambda x: x[0], reverse=True)[:top_k]
    
    results = []
    for sim, md, content in best_results:
        results.append({
            'similarity': float(sim),
            'conversation_id': md.get('conversation_id'),
            'title': md.get('title', 'Untitled'),
            'chunk_index': md.get('chunk_index'),
            'content_preview': content,
        })
    
    return {
        'query': query,
        'embed_time_ms': embed_time * 1000,
        'search_time_ms': search_time * 1000,
        'total_time_ms': (embed_time + search_time) * 1000,
        'top_k': top_k,
        'results': results,
        'similarity_stats': {
            'mean': float(np.mean([r['similarity'] for r in results])),
            'median': float(np.median([r['similarity'] for r in results])),
            'std': float(np.std([r['similarity'] for r in results])),
            'min': float(min([r['similarity'] for r in results])),
            'max': float(max([r['similarity'] for r in results])),
        } if results else {},
    }


def main():
    """Run benchmark and save results."""
    print("Loading current embedder and vectordb...")
    try:
        embedder = get_embedder()
        vectordb = get_vectordb()
        print(f"Model: sentence-transformers/all-MiniLM-L6-v2")
        print(f"Embedding dimension: {embedder.embed(['test']).shape[1]}")
    except Exception as e:
        print(f"Error loading embedder/vectordb: {e}")
        return
    
    # Test queries (including the problematic one)
    test_queries = [
        "spacetime as a simulation",
        "quantum mechanics",
        "database design",
        "API architecture",
        "machine learning",
        "conversation chunking strategy",
        "vector database search",
        "embedding model comparison",
    ]
    
    print(f"\nRunning {len(test_queries)} benchmark queries...")
    print("=" * 80)
    
    all_results = []
    total_embed_time = 0
    total_search_time = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}/{len(test_queries)}] Query: {query}")
        try:
            result = benchmark_query(query, embedder, vectordb, top_k=10)
            all_results.append(result)
            total_embed_time += result['embed_time_ms']
            total_search_time += result['search_time_ms']
            
            print(f"  Embed time: {result['embed_time_ms']:.2f}ms")
            print(f"  Search time: {result['search_time_ms']:.2f}ms")
            print(f"  Total time: {result['total_time_ms']:.2f}ms")
            print(f"  Top result similarity: {result['results'][0]['similarity']:.4f}" if result['results'] else "  No results")
            print(f"  Mean similarity: {result['similarity_stats'].get('mean', 0):.4f}")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"Total queries: {len(all_results)}")
    print(f"Average embed time: {total_embed_time / len(all_results):.2f}ms")
    print(f"Average search time: {total_search_time / len(all_results):.2f}ms")
    print(f"Average total time: {(total_embed_time + total_search_time) / len(all_results):.2f}ms")
    
    all_means = [r['similarity_stats'].get('mean', 0) for r in all_results if r['similarity_stats']]
    if all_means:
        print(f"Average mean similarity: {np.mean(all_means):.4f}")
        print(f"Similarity std across queries: {np.std(all_means):.4f}")
    
    # Save results
    output_file = project_root / "tests" / "benchmark_minilm_results.json"
    benchmark_data = {
        'model': 'sentence-transformers/all-MiniLM-L6-v2',
        'embedding_dim': int(embedder.embed(['test']).shape[1]),
        'timestamp': time.time(),
        'queries': all_results,
        'summary': {
            'total_queries': len(all_results),
            'avg_embed_time_ms': total_embed_time / len(all_results) if all_results else 0,
            'avg_search_time_ms': total_search_time / len(all_results) if all_results else 0,
            'avg_total_time_ms': (total_embed_time + total_search_time) / len(all_results) if all_results else 0,
            'avg_mean_similarity': float(np.mean(all_means)) if all_means else 0,
            'similarity_std': float(np.std(all_means)) if all_means else 0,
        },
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(benchmark_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_file}")
    print("\n[SUCCESS] Benchmark complete!")


if __name__ == "__main__":
    main()
