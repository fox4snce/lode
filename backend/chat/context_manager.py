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
    max_context_length: int = 4000,
    max_chunk_chars: int = 1200,
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

        header = (
            f"[Context {i} - Similarity: {similarity:.2f}]\n"
            f"Source: {title} (Chunk {chunk_idx})\n"
        )

        remaining = max_context_length - total_length
        if remaining <= 0:
            break

        # Always try to include at least the header; truncate content to fit the remaining budget.
        # This prevents the "No relevant context found." false-negative when chunks are large.
        min_needed = len(header) + 2  # "\n\n" after content
        if remaining < min_needed:
            break

        # Cap each chunk so one huge chunk doesn't crowd out the others.
        # This is critical for good RAG behavior (multiple, diverse evidence snippets).
        per_chunk_cap = max(200, int(max_chunk_chars))
        max_content_len = min(per_chunk_cap, remaining - len(header) - 2)
        safe_content = content or ""
        if len(safe_content) > max_content_len:
            # Reserve a small suffix for an ellipsis marker when truncating.
            if max_content_len > 30:
                safe_content = safe_content[: max_content_len - 3].rstrip() + "..."
            else:
                safe_content = safe_content[:max_content_len]

        chunk_text = f"{header}{safe_content}\n\n"

        parts.append(chunk_text)
        total_length += len(chunk_text)
    
    return "\n".join(parts) if parts else "No relevant context found."
