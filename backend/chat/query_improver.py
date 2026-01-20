"""
Query improvement for better vector search results.

Uses LLM to transform user queries into search-optimized queries.
"""

from typing import List, Dict, Optional
from backend.llm.litellm_service import call_llm


def format_history(history: List[Dict[str, str]], max_exchanges: int = 3) -> str:
    """Format conversation history for context."""
    if not history:
        return ""
    
    # Get last N exchanges
    recent = history[-max_exchanges * 2:] if len(history) > max_exchanges * 2 else history
    
    parts = []
    for msg in recent:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        parts.append(f"{role}: {content}")
    
    return "\n".join(parts)


def improve_query_for_search(
    user_query: str,
    model: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Improve user query for better vector search results.
    
    Uses LLM to:
    - Extract key concepts
    - Remove conversational fluff
    - Focus on searchable terms
    - Consider conversation context
    
    Args:
        user_query: Original user query
        model: LLM model to use for improvement
        conversation_history: Optional conversation history for context
    
    Returns:
        Improved query string (falls back to original on error)
    """
    system_prompt = """You are a query improvement assistant. Your job is to transform user queries into concise, search-optimized queries for semantic search.

Focus on:
- Key concepts and entities
- Core intent
- Searchable terms

Remove:
- Conversational filler
- Pronouns that need context
- Vague references

If the query is already clear and concise, return it as-is. Keep it short (under 20 words)."""

    # Include recent history for context
    context = ""
    if conversation_history:
        recent = format_history(conversation_history, max_exchanges=3)
        context = f"\n\nRecent conversation:\n{recent}"
    
    prompt = f"""User query: {user_query}{context}

Provide an improved search query:"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    try:
        improved = call_llm(messages, model, temperature=0.3, max_tokens=100)
        improved = improved.strip()
        
        # Fallback to original if empty or error-like
        if not improved or improved.startswith("Error"):
            return user_query
        
        return improved
    except Exception:
        # On any error, return original query
        return user_query
