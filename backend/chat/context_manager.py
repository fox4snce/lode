"""
Context management for chat feature.

Handles filtering and formatting vector search results for LLM context.
"""

from typing import List, Dict, Any


def filter_results_by_quality(
    results: List[Dict[str, Any]],
    min_similarity: float = 0.5,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Filter vector search results by quality.
    
    Args:
        results: List of search result dicts with "similarity" key
        min_similarity: Minimum similarity score (0.0-1.0)
        max_results: Maximum number of results to return
    
    Returns:
        Filtered and sorted results (highest similarity first)
    """
    if not results:
        return []
    
    # Filter by minimum similarity
    filtered = [
        r for r in results 
        if r.get("similarity", 0) >= min_similarity
    ]
    
    # Sort by similarity (descending)
    filtered.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    
    # Limit to max_results
    return filtered[:max_results]


def format_context_for_llm(
    results: List[Dict[str, Any]],
    max_context_length: int = 4000
) -> str:
    """
    Format search results into LLM context.
    
    Args:
        results: List of search result dicts
        max_context_length: Maximum character length for context
    
    Returns:
        Formatted context string
    """
    if not results:
        return "No relevant context found."
    
    parts = []
    total_length = 0
    
    for i, result in enumerate(results, 1):
        content = result.get("content", "")
        similarity = result.get("similarity", 0.0)
        metadata = result.get("metadata", {})
        title = metadata.get("title", "Unknown")
        chunk_idx = metadata.get("chunk_index", 0)
        
        chunk_text = f"[Context {i} - Similarity: {similarity:.2f}]\n"
        chunk_text += f"Source: {title} (Chunk {chunk_idx})\n"
        chunk_text += f"{content}\n\n"
        
        if total_length + len(chunk_text) > max_context_length:
            break
        
        parts.append(chunk_text)
        total_length += len(chunk_text)
    
    return "\n".join(parts) if parts else "No relevant context found."
