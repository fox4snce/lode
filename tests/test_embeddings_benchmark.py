"""
Benchmark ONNX embeddings provider vs API-based embeddings.

Tests performance (speed) and compares results.
"""
import time
import sqlite3
import json
import hashlib
from typing import List
import numpy as np
import urllib.request

from embeddings_onnx import OfflineEmbedder, get_text_hash

# Configuration
DB_PATH = 'conversations.db'
EMBEDDINGS_URL = 'http://localhost:1234/v1/embeddings'
EMBEDDINGS_MODEL = 'text-embedding-nomic-embed-text-v1.5'

# Test data sizes
TEST_SIZES = [1, 10, 50, 100, 200]
BATCH_SIZE = 32


def get_test_texts_from_db(count: int = 100) -> List[str]:
    """Extract sample texts from database conversations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('''
        SELECT content 
        FROM messages 
        WHERE content IS NOT NULL AND LENGTH(content) > 50
        ORDER BY RANDOM()
        LIMIT ?
    ''', (count,))
    
    texts = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # If not enough in DB, generate some test texts
    while len(texts) < count:
        texts.append(f"Sample text {len(texts)}: This is a test sentence for embedding generation.")
    
    return texts[:count]


def benchmark_onnx(texts: List[str], embedder: OfflineEmbedder) -> dict:
    """Benchmark ONNX embeddings."""
    print(f"\n[ONNX] Embedding {len(texts)} texts...")
    
    # Warmup
    embedder.embed(texts[:min(5, len(texts))], batch_size=BATCH_SIZE)
    
    # Actual benchmark
    start = time.time()
    embeddings = embedder.embed(texts, batch_size=BATCH_SIZE)
    elapsed = time.time() - start
    
    return {
        'method': 'ONNX (CPU)',
        'count': len(texts),
        'time_seconds': elapsed,
        'time_per_text_ms': (elapsed / len(texts)) * 1000,
        'throughput_texts_per_sec': len(texts) / elapsed if elapsed > 0 else 0,
        'embedding_shape': embeddings.shape,
        'embeddings': embeddings
    }


def benchmark_api(texts: List[str], cache_conn: sqlite3.Connection = None) -> dict:
    """Benchmark API-based embeddings (with caching)."""
    print(f"\n[API] Embedding {len(texts)} texts...")
    
    # Check cache first
    cached_embeddings = {}
    uncached_texts = []
    uncached_indices = []
    
    if cache_conn:
        for i, text in enumerate(texts):
            text_hash = get_text_hash(text)
            cursor = cache_conn.execute('''
                SELECT vector FROM embedding_cache
                WHERE text_hash = ? AND model = ?
            ''', (text_hash, EMBEDDINGS_MODEL))
            row = cursor.fetchone()
            if row:
                cached_embeddings[i] = json.loads(row[0])
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
    else:
        uncached_texts = texts
        uncached_indices = list(range(len(texts)))
    
    # If all cached, return cached results
    if not uncached_texts:
        print(f"  [API] All {len(texts)} texts found in cache (instant)")
        embeddings_list = [cached_embeddings[i] for i in range(len(texts))]
        return {
            'method': 'API (cached)',
            'count': len(texts),
            'time_seconds': 0.001,  # Minimal time for cache lookup
            'time_per_text_ms': 0.001,
            'throughput_texts_per_sec': len(texts) / 0.001,
            'embedding_shape': (len(texts), len(embeddings_list[0])),
            'embeddings': np.array(embeddings_list),
            'cached': True
        }
    
    # Call API for uncached texts
    print(f"  [API] {len(uncached_texts)} texts need embedding (cache miss)")
    
    data = {
        "model": EMBEDDINGS_MODEL,
        "input": uncached_texts
    }
    req = urllib.request.Request(
        EMBEDDINGS_URL,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            embeddings = [item['embedding'] for item in result['data']]
    except Exception as e:
        print(f"  [ERROR] API call failed: {e}")
        return None
    
    elapsed = time.time() - start
    
    # Cache the embeddings
    if cache_conn:
        for i, text, embedding in zip(uncached_indices, uncached_texts, embeddings):
            text_hash = get_text_hash(text)
            cache_conn.execute('''
                INSERT OR REPLACE INTO embedding_cache (text_hash, model, vector)
                VALUES (?, ?, ?)
            ''', (text_hash, EMBEDDINGS_MODEL, json.dumps(embedding)))
        cache_conn.commit()
    
    # Combine cached and new embeddings
    result_embeddings = []
    cached_idx = 0
    for i in range(len(texts)):
        if i in cached_embeddings:
            result_embeddings.append(cached_embeddings[i])
        else:
            result_embeddings.append(embeddings[cached_idx])
            cached_idx += 1
    
    return {
        'method': 'API (LM Studio)',
        'count': len(texts),
        'time_seconds': elapsed,
        'time_per_text_ms': (elapsed / len(uncached_texts)) * 1000 if uncached_texts else 0,
        'throughput_texts_per_sec': len(uncached_texts) / elapsed if elapsed > 0 and uncached_texts else 0,
        'embedding_shape': (len(texts), len(result_embeddings[0])),
        'embeddings': np.array(result_embeddings),
        'cached': False,
        'cached_count': len(cached_embeddings),
        'uncached_count': len(uncached_texts)
    }


def compare_embeddings(emb1: np.ndarray, emb2: np.ndarray) -> dict:
    """Compare two embedding arrays (must be same length)."""
    if emb1.shape != emb2.shape:
        return {'error': f'Shape mismatch: {emb1.shape} vs {emb2.shape}'}
    
    # Compute pairwise cosine similarities
    # Normalize both (they should already be normalized, but be safe)
    emb1_norm = emb1 / (np.linalg.norm(emb1, axis=1, keepdims=True) + 1e-12)
    emb2_norm = emb2 / (np.linalg.norm(emb2, axis=1, keepdims=True) + 1e-12)
    
    similarities = np.diag(np.dot(emb1_norm, emb2_norm.T))
    
    return {
        'mean_similarity': float(np.mean(similarities)),
        'min_similarity': float(np.min(similarities)),
        'max_similarity': float(np.max(similarities)),
        'std_similarity': float(np.std(similarities))
    }


def main():
    print("=" * 70)
    print("Embeddings Benchmark: ONNX vs API")
    print("=" * 70)
    
    # Load ONNX embedder
    print("\n[1/4] Loading ONNX embedder...")
    try:
        embedder = OfflineEmbedder.load()
        print(f"  [SUCCESS] ONNX embedder loaded")
        print(f"  Model: vendor/embedder_minilm_l6_v2")
        print(f"  Max length: {embedder.max_length} tokens")
    except Exception as e:
        print(f"  [ERROR] Failed to load ONNX embedder: {e}")
        return
    
    # Get test texts
    print("\n[2/4] Loading test texts from database...")
    max_test_size = max(TEST_SIZES)
    test_texts = get_test_texts_from_db(max_test_size)
    print(f"  Loaded {len(test_texts)} test texts")
    
    # Connect to cache DB
    cache_conn = sqlite3.connect(DB_PATH)
    cache_conn.execute('PRAGMA journal_mode=WAL')
    
    # Run benchmarks
    print("\n[3/4] Running benchmarks...")
    results = []
    
    for size in TEST_SIZES:
        if size > len(test_texts):
            continue
        
        texts = test_texts[:size]
        print(f"\n{'='*70}")
        print(f"Testing with {size} texts")
        print(f"{'='*70}")
        
        # Benchmark ONNX
        try:
            onnx_result = benchmark_onnx(texts, embedder)
            results.append(onnx_result)
            print(f"  [ONNX] {onnx_result['time_seconds']:.3f}s total | "
                  f"{onnx_result['time_per_text_ms']:.2f}ms/text | "
                  f"{onnx_result['throughput_texts_per_sec']:.1f} texts/sec")
        except Exception as e:
            print(f"  [ERROR] ONNX benchmark failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Benchmark API (if available)
        try:
            api_result = benchmark_api(texts, cache_conn)
            if api_result:
                results.append(api_result)
                if api_result.get('cached'):
                    print(f"  [API] All cached (instant)")
                else:
                    print(f"  [API] {api_result['time_seconds']:.3f}s total | "
                          f"{api_result['time_per_text_ms']:.2f}ms/text | "
                          f"{api_result['throughput_texts_per_sec']:.1f} texts/sec")
                    if api_result.get('cached_count', 0) > 0:
                        print(f"         ({api_result['cached_count']} cached, {api_result['uncached_count']} new)")
        except Exception as e:
            print(f"  [WARNING] API benchmark failed (API may not be running): {e}")
    
    cache_conn.close()
    
    # Print summary
    print(f"\n{'='*70}")
    print("[4/4] Summary")
    print(f"{'='*70}\n")
    
    print(f"{'Method':<20} {'Count':<8} {'Time (s)':<12} {'ms/text':<12} {'texts/sec':<12}")
    print("-" * 70)
    
    for r in results:
        method = r['method']
        count = r['count']
        time_s = r['time_seconds']
        ms_per = r['time_per_text_ms']
        throughput = r['throughput_texts_per_sec']
        
        print(f"{method:<20} {count:<8} {time_s:<12.3f} {ms_per:<12.2f} {throughput:<12.1f}")
    
    print(f"\n{'='*70}")
    print("[NOTE] ONNX embeddings are 384-dimensional (all-MiniLM-L6-v2)")
    print("       API embeddings may have different dimensions depending on model")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

