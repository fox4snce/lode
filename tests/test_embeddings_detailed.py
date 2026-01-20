"""
Detailed performance test for ONNX embeddings provider.

Tests:
- Single text embedding
- Batch embedding (various sizes)
- Memory usage
- Consistency (same text -> same embedding)
"""
import time
import numpy as np
from embeddings_onnx import OfflineEmbedder

# Test texts of various lengths
SHORT_TEXT = "This is a short test."
MEDIUM_TEXT = """
This is a medium-length text that contains multiple sentences.
It describes a typical business conversation about project planning.
The team needs to discuss the Q4 roadmap and prioritize features.
We should schedule a meeting to review the requirements.
"""
LONG_TEXT = """
This is a longer text that simulates a real conversation transcript.
It contains multiple paragraphs and discusses various topics.
The conversation covers product development, team coordination, and technical challenges.
We need to address the database migration issues first.
Then we can move on to the API design review.
The client integration requires careful planning and testing.
We should set up a staging environment before deploying to production.
The team needs to coordinate with the DevOps team for infrastructure changes.
Let's schedule a follow-up meeting to discuss the implementation details.
We also need to consider the performance implications of the new architecture.
The security review should be completed before the final deployment.
"""

BATCH_SIZES = [1, 5, 10, 32, 64, 100]
REPEAT_COUNT = 5  # For consistency testing


def test_single_embedding(embedder: OfflineEmbedder):
    """Test single text embedding performance."""
    print("\n" + "="*70)
    print("Test 1: Single Text Embedding")
    print("="*70)
    
    texts = [SHORT_TEXT, MEDIUM_TEXT, LONG_TEXT]
    
    for text in texts:
        word_count = len(text.split())
        char_count = len(text)
        
        times = []
        for _ in range(REPEAT_COUNT):
            start = time.time()
            embedding = embedder.embed_single(text)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = np.mean(times)
        std_time = np.std(times)
        
        print(f"\n  Text: {word_count} words, {char_count} chars")
        print(f"    Time: {avg_time*1000:.2f}ms ± {std_time*1000:.2f}ms")
        print(f"    Embedding shape: {embedding.shape}")
        print(f"    Embedding norm: {np.linalg.norm(embedding):.4f}")


def test_batch_embedding(embedder: OfflineEmbedder):
    """Test batch embedding performance."""
    print("\n" + "="*70)
    print("Test 2: Batch Embedding Performance")
    print("="*70)
    
    # Create a pool of texts
    text_pool = [SHORT_TEXT, MEDIUM_TEXT, LONG_TEXT] * 50  # 150 texts total
    
    print(f"\n  Testing with text pool of {len(text_pool)} texts")
    print(f"  {'Batch Size':<15} {'Time (s)':<15} {'ms/text':<15} {'texts/sec':<15} {'Speedup':<15}")
    print("  " + "-"*70)
    
    baseline_time = None
    
    for batch_size in BATCH_SIZES:
        if batch_size > len(text_pool):
            continue
        
        texts = text_pool[:batch_size]
        
        # Warmup
        embedder.embed(texts[:min(5, len(texts))], batch_size=min(batch_size, 32))
        
        # Benchmark
        times = []
        for _ in range(3):
            start = time.time()
            embeddings = embedder.embed(texts, batch_size=batch_size)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = np.mean(times)
        ms_per_text = (avg_time / len(texts)) * 1000
        texts_per_sec = len(texts) / avg_time
        
        if baseline_time is None:
            baseline_time = avg_time
            speedup = 1.0
        else:
            speedup = baseline_time / avg_time
        
        print(f"  {batch_size:<15} {avg_time:<15.3f} {ms_per_text:<15.2f} {texts_per_sec:<15.1f} {speedup:<15.2f}x")


def test_consistency(embedder: OfflineEmbedder):
    """Test that same text produces same embedding."""
    print("\n" + "="*70)
    print("Test 3: Consistency (Same Text -> Same Embedding)")
    print("="*70)
    
    test_text = MEDIUM_TEXT
    
    # Generate embeddings multiple times
    embeddings = []
    for _ in range(REPEAT_COUNT):
        emb = embedder.embed_single(test_text)
        embeddings.append(emb)
    
    embeddings = np.array(embeddings)
    
    # Check if all embeddings are identical
    first_emb = embeddings[0]
    max_diff = 0.0
    for i in range(1, len(embeddings)):
        diff = np.max(np.abs(embeddings[i] - first_emb))
        max_diff = max(max_diff, diff)
    
    print(f"\n  Generated {REPEAT_COUNT} embeddings for same text")
    print(f"  Max difference between embeddings: {max_diff:.2e}")
    
    if max_diff < 1e-6:
        print(f"  [SUCCESS] Embeddings are consistent (deterministic)")
    else:
        print(f"  [WARNING] Embeddings vary (may be non-deterministic)")


def test_similarity(embedder: OfflineEmbedder):
    """Test semantic similarity between related texts."""
    print("\n" + "="*70)
    print("Test 4: Semantic Similarity")
    print("="*70)
    
    texts = [
        "I need help with database migration",
        "We should migrate the database to the new server",
        "The database migration process needs attention",
        "What's the weather like today?",
        "I love eating pizza for dinner"
    ]
    
    embeddings = embedder.embed(texts)
    
    print(f"\n  Computing cosine similarities between {len(texts)} texts:")
    print(f"  {'Text 1':<40} {'Text 2':<40} {'Similarity':<12}")
    print("  " + "-"*95)
    
    for i in range(len(texts)):
        for j in range(i+1, len(texts)):
            sim = np.dot(embeddings[i], embeddings[j])
            t1 = texts[i][:38] + ".." if len(texts[i]) > 40 else texts[i]
            t2 = texts[j][:38] + ".." if len(texts[j]) > 40 else texts[j]
            print(f"  {t1:<40} {t2:<40} {sim:<12.4f}")


def test_memory_usage(embedder: OfflineEmbedder):
    """Test memory usage with large batches."""
    print("\n" + "="*70)
    print("Test 5: Memory Usage (Large Batch)")
    print("="*70)
    
    # Create a large batch
    large_batch = [MEDIUM_TEXT] * 500
    
    print(f"\n  Embedding {len(large_batch)} texts...")
    
    start = time.time()
    embeddings = embedder.embed(large_batch, batch_size=64)
    elapsed = time.time() - start
    
    # Estimate memory (rough)
    embedding_size_mb = (embeddings.nbytes / (1024 * 1024))
    
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Embeddings size: {embedding_size_mb:.2f} MB")
    print(f"  Throughput: {len(large_batch)/elapsed:.1f} texts/sec")


def main():
    print("="*70)
    print("ONNX Embeddings Provider - Detailed Performance Test")
    print("="*70)
    
    # Load embedder
    print("\n[Loading] ONNX embedder...")
    try:
        embedder = OfflineEmbedder.load()
        print(f"  [SUCCESS] Loaded model from vendor/embedder_bge_small_v1_5 (BGE-small-en-v1.5)")
        print(f"  Max sequence length: {embedder.max_length} tokens")
    except Exception as e:
        print(f"  [ERROR] Failed to load: {e}")
        return
    
    # Run tests
    test_single_embedding(embedder)
    test_batch_embedding(embedder)
    test_consistency(embedder)
    test_similarity(embedder)
    test_memory_usage(embedder)
    
    print("\n" + "="*70)
    print("[COMPLETE] All tests finished")
    print("="*70)


if __name__ == "__main__":
    main()

