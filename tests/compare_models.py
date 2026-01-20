"""
Compare two embedding models side-by-side on the same queries.

Loads benchmark results from MiniLM and runs the same queries with BGE-small,
then generates a comparison report.
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
from backend.vectordb.service import get_vectordb
from embeddings_onnx import OfflineEmbedder


def benchmark_query(
    query: str,
    embedder,
    vectordb,
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


def load_minilm_benchmark() -> Dict:
    """Load the saved MiniLM benchmark results."""
    benchmark_file = project_root / "tests" / "benchmark_minilm_results.json"
    if not benchmark_file.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_file}")
    
    with open(benchmark_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_models():
    """Compare MiniLM and BGE-small models."""
    print("=" * 80)
    print("MODEL COMPARISON: MiniLM-L6-v2 vs BGE-small-en-v1.5")
    print("=" * 80)
    
    # Load MiniLM benchmark
    print("\n[1/3] Loading MiniLM benchmark results...")
    minilm_data = load_minilm_benchmark()
    queries = [q['query'] for q in minilm_data['queries']]
    print(f"  Loaded {len(queries)} queries from MiniLM benchmark")
    
    # Load BGE-small embedder
    print("\n[2/3] Loading BGE-small embedder...")
    try:
        bge_embedder = OfflineEmbedder.load(model_dir="vendor/embedder_bge_small_v1_5")
        print(f"  Model: BAAI/bge-small-en-v1.5")
        print(f"  Embedding dimension: {bge_embedder.embed(['test']).shape[1]}")
    except Exception as e:
        print(f"  ERROR: Could not load BGE-small model: {e}")
        print(f"  Make sure you've exported it: python tools/export_embedder_onnx.py --model bge-small")
        return
    
    # Load vectordb (should be re-indexed with BGE-small)
    print("\n[3/3] Loading vectordb...")
    vectordb = get_vectordb()
    print(f"  Vectordb loaded")
    
    # Run BGE-small benchmark
    print(f"\nRunning {len(queries)} queries with BGE-small...")
    print("=" * 80)
    
    bge_results = []
    total_embed_time = 0
    total_search_time = 0
    
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Query: {query}")
        try:
            result = benchmark_query(query, bge_embedder, vectordb, top_k=10)
            bge_results.append(result)
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
    
    # Generate comparison
    print("\n" + "=" * 80)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 80)
    
    minilm_queries = {q['query']: q for q in minilm_data['queries']}
    bge_queries = {q['query']: q for q in bge_results}
    
    print(f"\n{'Query':<40} {'MiniLM Time':<15} {'BGE Time':<15} {'MiniLM Sim':<12} {'BGE Sim':<12} {'Diff':<10}")
    print("-" * 110)
    
    for query in queries:
        ml = minilm_queries.get(query, {})
        bg = bge_queries.get(query, {})
        
        ml_time = ml.get('total_time_ms', 0)
        bg_time = bg.get('total_time_ms', 0)
        ml_sim = ml.get('similarity_stats', {}).get('mean', 0)
        bg_sim = bg.get('similarity_stats', {}).get('mean', 0)
        time_diff = ((bg_time - ml_time) / ml_time * 100) if ml_time > 0 else 0
        
        print(f"{query[:38]:<40} {ml_time:>8.1f}ms     {bg_time:>8.1f}ms     {ml_sim:>8.4f}     {bg_sim:>8.4f}     {time_diff:>+6.1f}%")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    ml_avg_time = minilm_data['summary']['avg_total_time_ms']
    bg_avg_time = (total_embed_time + total_search_time) / len(bge_results) if bge_results else 0
    
    ml_avg_sim = minilm_data['summary']['avg_mean_similarity']
    bg_avg_sim = np.mean([r['similarity_stats'].get('mean', 0) for r in bge_results if r['similarity_stats']])
    
    ml_sim_std = minilm_data['summary']['similarity_std']
    bg_sim_std = np.std([r['similarity_stats'].get('mean', 0) for r in bge_results if r['similarity_stats']])
    
    print(f"\nAverage Query Time:")
    print(f"  MiniLM: {ml_avg_time:.2f}ms")
    print(f"  BGE-small: {bg_avg_time:.2f}ms")
    print(f"  Difference: {((bg_avg_time - ml_avg_time) / ml_avg_time * 100):+.1f}%")
    
    print(f"\nAverage Similarity Score:")
    print(f"  MiniLM: {ml_avg_sim:.4f} (std: {ml_sim_std:.4f})")
    print(f"  BGE-small: {bg_avg_sim:.4f} (std: {bg_sim_std:.4f})")
    print(f"  Difference: {bg_avg_sim - ml_avg_sim:+.4f}")
    
    print(f"\nInterpretation:")
    if bg_sim_std > ml_sim_std:
        print(f"  [OK] BGE-small has higher variance in scores (better discrimination)")
    if bg_avg_sim < ml_avg_sim:
        print(f"  [OK] BGE-small has lower average similarity (less 'blurry' embeddings)")
    if bg_avg_time < ml_avg_time * 3:
        print(f"  [OK] BGE-small is within 3x speed of MiniLM (acceptable)")
    
    print(f"\nRecommendation:")
    if bg_avg_sim < ml_avg_sim - 0.10 and bg_sim_std > ml_sim_std:
        print(f"  STRONGLY RECOMMEND switching to BGE-small:")
        print(f"    - Lower similarity scores indicate better discrimination")
        print(f"    - Higher variance means more accurate relevance ranking")
        print(f"    - Performance is similar or better")
    elif bg_avg_sim < ml_avg_sim:
        print(f"  Consider switching to BGE-small for better quality")
    else:
        print(f"  MiniLM may be sufficient for your use case")
    
    # Save comparison
    comparison_file = project_root / "tests" / "model_comparison.json"
    comparison_data = {
        'minilm': minilm_data,
        'bge_small': {
            'model': 'BAAI/bge-small-en-v1.5',
            'embedding_dim': int(bge_embedder.embed(['test']).shape[1]),
            'timestamp': time.time(),
            'queries': bge_results,
            'summary': {
                'total_queries': len(bge_results),
                'avg_embed_time_ms': total_embed_time / len(bge_results) if bge_results else 0,
                'avg_search_time_ms': total_search_time / len(bge_results) if bge_results else 0,
                'avg_total_time_ms': (total_embed_time + total_search_time) / len(bge_results) if bge_results else 0,
                'avg_mean_similarity': float(bg_avg_sim),
                'similarity_std': float(bg_sim_std),
            },
        },
        'comparison': {
            'time_ratio': bg_avg_time / ml_avg_time if ml_avg_time > 0 else 0,
            'similarity_diff': bg_avg_sim - ml_avg_sim,
            'similarity_std_ratio': bg_sim_std / ml_sim_std if ml_sim_std > 0 else 0,
        },
    }
    
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nComparison saved to: {comparison_file}")
    print("\n[SUCCESS] Comparison complete!")


if __name__ == "__main__":
    compare_models()
