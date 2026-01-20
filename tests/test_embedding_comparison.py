"""
Compare embedding models on real queries to diagnose quality issues.

This script:
1. Tests current model (MiniLM-L6-v2) on sample queries
2. Can test alternative models (BGE-small, E5-small, etc.) if available
3. Analyzes similarity score distributions and relevance
4. Helps identify if model upgrade would help
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from typing import List, Dict, Tuple
from backend.vectordb.service import get_vectordb, get_embedder
from backend.vectordb.sqlite_vectordb import SQLiteVectorDB


def analyze_query(
    query: str,
    embedder,
    vectordb: SQLiteVectorDB,
    top_k: int = 10,
) -> Dict:
    """Run a query and analyze the results."""
    # Embed query
    query_emb = embedder.embed([query])[0]
    
    # Search
    rows = vectordb.search_fast(query_emb.tolist(), top_n=top_k * 5, filters={'type': 'chunk'})
    
    # Analyze results
    similarities = [r.similarity for r in rows[:top_k]]
    metadata_list = [r.metadata or {} for r in rows[:top_k]]
    contents = [r.content[:200] for r in rows[:top_k]]  # First 200 chars
    
    # Best per conversation (like the real search does)
    best_by_conv: Dict[str, Tuple[float, Dict]] = {}
    for r in rows:
        md = r.metadata or {}
        conv_id = md.get("conversation_id") or r.file_id or ""
        prev = best_by_conv.get(conv_id)
        if prev is None or r.similarity > prev[0]:
            best_by_conv[conv_id] = (r.similarity, md)
    
    best_sims = sorted([s for s, _ in best_by_conv.values()], reverse=True)[:top_k]
    
    return {
        'query': query,
        'raw_top_k_similarities': similarities,
        'best_per_conv_similarities': best_sims,
        'mean_similarity': np.mean(similarities),
        'median_similarity': np.median(similarities),
        'std_similarity': np.std(similarities),
        'min_similarity': np.min(similarities),
        'max_similarity': np.max(similarities),
        'results': [
            {
                'similarity': sim,
                'content_preview': content,
                'metadata': md,
            }
            for sim, content, md in zip(similarities, contents, metadata_list)
        ],
    }


def print_analysis(analysis: Dict, model_name: str):
    """Print formatted analysis results."""
    import sys
    import io
    
    # Use UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print(f"\n{'='*80}")
    print(f"Model: {model_name}")
    print(f"Query: {analysis['query']}")
    print(f"{'='*80}")
    print(f"Similarity Statistics:")
    print(f"  Mean:   {analysis['mean_similarity']:.4f}")
    print(f"  Median: {analysis['median_similarity']:.4f}")
    print(f"  Std:    {analysis['std_similarity']:.4f}")
    print(f"  Range:  {analysis['min_similarity']:.4f} - {analysis['max_similarity']:.4f}")
    print(f"\nTop {len(analysis['results'])} Results:")
    for i, result in enumerate(analysis['results'], 1):
        md = result['metadata']
        title = md.get('title', 'Untitled')[:50]
        chunk_idx = md.get('chunk_index', '?')
        preview = result['content_preview'][:150].encode('ascii', errors='replace').decode('ascii')
        print(f"\n  {i}. Similarity: {result['similarity']:.4f}")
        print(f"     From: {title} (Chunk {chunk_idx})")
        print(f"     Preview: {preview}...")
    print(f"\nBest-per-conversation similarities: {[f'{s:.4f}' for s in analysis['best_per_conv_similarities'][:5]]}")


def main():
    """Run comparison analysis."""
    print("Loading current embedder and vectordb...")
    try:
        embedder = get_embedder()
        vectordb = get_vectordb()
    except Exception as e:
        print(f"Error loading embedder/vectordb: {e}")
        print("Make sure vectordb is indexed and embedder is available.")
        return
    
    # Test queries (including the problematic one)
    test_queries = [
        "spacetime as a simulation",
        "quantum mechanics",
        "database design",
        "API architecture",
        "machine learning",
    ]
    
    print(f"\nAnalyzing {len(test_queries)} queries with current model...")
    print("Model: sentence-transformers/all-MiniLM-L6-v2")
    
    all_analyses = []
    for query in test_queries:
        try:
            analysis = analyze_query(query, embedder, vectordb, top_k=10)
            all_analyses.append(analysis)
            print_analysis(analysis, "MiniLM-L6-v2")
        except Exception as e:
            print(f"Error analyzing query '{query}': {e}")
            import traceback
            traceback.print_exc()
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY ACROSS ALL QUERIES")
    print(f"{'='*80}")
    all_means = [a['mean_similarity'] for a in all_analyses]
    all_medians = [a['median_similarity'] for a in all_analyses]
    all_stds = [a['std_similarity'] for a in all_analyses]
    
    print(f"Mean similarity across queries: {np.mean(all_means):.4f} ± {np.std(all_means):.4f}")
    print(f"Median similarity across queries: {np.mean(all_medians):.4f} ± {np.std(all_medians):.4f}")
    print(f"Std deviation across queries: {np.mean(all_stds):.4f}")
    
    print(f"\nInterpretation:")
    print(f"- If mean similarity is >0.80, the model may be producing 'blurry' embeddings")
    print(f"- If std is <0.05, scores are too clustered (everything seems similar)")
    print(f"- If scores don't match relevance, consider upgrading to BGE-small or E5-small")
    
    print(f"\n{'='*80}")
    print("RECOMMENDATION:")
    if np.mean(all_means) > 0.80:
        print("[WARNING] High similarity scores suggest model may be too weak.")
        print("   Consider upgrading to BGE-small-en-v1.5 or E5-small-v2")
    elif np.mean(all_stds) < 0.05:
        print("[WARNING] Low variance in scores suggests embeddings are too similar.")
        print("   Consider upgrading to a model with more dimensions (768+)")
    else:
        print("[OK] Similarity scores look reasonable. Issue may be in chunking or ranking.")


if __name__ == "__main__":
    main()
