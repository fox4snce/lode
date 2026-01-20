"""
History management for chat feature.

Handles sliding window for conversation history.
"""

from typing import List, Dict, Any, Optional, Callable


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (1 token ≈ 4 characters).
    
    This is a simple heuristic. For more accurate estimation,
    you'd need to use a tokenizer, but this works well enough
    for sliding window purposes.
    """
    return len(text) // 4


def apply_sliding_window(
    messages: List[Dict[str, str]],
    max_tokens: int = 4000,
    token_estimator: Optional[Callable[[str], int]] = None
) -> List[Dict[str, str]]:
    """
    Apply sliding window to conversation history.
    
    Keeps:
    - System message (always)
    - Most recent messages (within token limit)
    
    Args:
        messages: List of message dicts with "role" and "content"
        max_tokens: Maximum tokens to keep
        token_estimator: Optional function to estimate tokens (default: estimate_tokens)
    
    Returns:
        Windowed message list
    """
    if not messages:
        return []
    
    if token_estimator is None:
        token_estimator = estimate_tokens
    
    # System message always included
    system_msg = None
    if messages and messages[0].get("role") == "system":
        system_msg = messages[0]
        messages = messages[1:]
    
    # Keep most recent messages that fit
    window = []
    total_tokens = 0
    
    # Process from most recent to oldest
    for msg in reversed(messages):
        content = msg.get("content", "")
        tokens = token_estimator(content)
        
        if total_tokens + tokens > max_tokens:
            break
        
        window.insert(0, msg)
        total_tokens += tokens
    
    # Re-add system message
    if system_msg:
        window.insert(0, system_msg)
    
    return window
