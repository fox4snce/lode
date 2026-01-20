"""
Chat API routes for RAG chat feature (Pro only).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from backend.feature_flags import is_feature_enabled
from backend.llm.litellm_service import call_llm, get_available_providers
from backend.chat.query_improver import improve_query_for_search
from backend.chat.context_manager import filter_results_by_quality, format_context_for_llm
from backend.chat.history_manager import apply_sliding_window
from backend.vectordb.service import search_phrases

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    """Chat completion request."""
    query: str
    model: str  # e.g., "openai/gpt-4o"
    history: List[ChatMessage] = []
    context_window_size: int = 4000  # tokens
    min_similarity: float = 0.5
    max_context_chunks: int = 5


class ChatResponse(BaseModel):
    """Chat completion response."""
    response: str
    improved_query: str
    context_chunks_used: int
    similarity_scores: List[float]


async def search_vectordb(query: str, max_chunks: int) -> List[Dict[str, Any]]:
    """Search vector database (async wrapper)."""
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        lambda: search_phrases(
            phrases=[query],
            top_k=max_chunks * 2,  # Get more candidates for filtering
            min_similarity=None,  # Filter later
            filters={"type": "chunk"},
            include_content=True,
        )
    )
    
    # Extract results from response
    if results and len(results) > 0:
        return results[0].get("results", [])
    return []


@router.post("/completion", response_model=ChatResponse)
async def chat_completion(request: ChatRequest) -> ChatResponse:
    """Main chat completion endpoint."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    
    try:
        # Convert history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]
        
        # 1. Improve query
        improved_query = improve_query_for_search(
            request.query,
            request.model,
            history
        )
        
        # 2. Search vector database
        search_results = await search_vectordb(improved_query, request.max_context_chunks)
        
        # 3. Filter by quality
        filtered = filter_results_by_quality(
            search_results,
            request.min_similarity,
            request.max_context_chunks
        )
        
        # 4. Format context
        context = format_context_for_llm(filtered)
        
        # 5. Apply sliding window to history
        windowed_history = apply_sliding_window(
            history,
            request.context_window_size
        )
        
        # 6. Build messages for LLM
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "Use the context information to provide accurate and relevant answers. "
            "If the context doesn't contain relevant information, say so clearly. "
            "Cite sources when referencing specific information from the context."
        )
        
        # Ensure system message is first
        if not windowed_history or windowed_history[0].get("role") != "system":
            windowed_history.insert(0, {"role": "system", "content": system_prompt})
        else:
            windowed_history[0]["content"] = system_prompt
        
        # Add context and current query
        user_message = f"""Context information:

{context}

---

User question: {request.query}

Please provide a helpful answer based on the context above."""
        
        messages = windowed_history + [
            {"role": "user", "content": user_message}
        ]
        
        # 7. Call LLM (temperature=0.7 for consistent, focused responses)
        response_text = call_llm(
            messages,
            request.model,
            temperature=0.7,
            max_tokens=2048
        )
        
        return ChatResponse(
            response=response_text,
            improved_query=improved_query,
            context_chunks_used=len(filtered),
            similarity_scores=[r.get("similarity", 0) for r in filtered]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


@router.get("/providers")
async def get_providers():
    """Get list of available LLM providers."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    
    try:
        providers = get_available_providers()
        return {"providers": providers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get providers: {str(e)}")


class TestModelRequest(BaseModel):
    """Test model request."""
    provider: str
    model: str


class TestModelResponse(BaseModel):
    """Test model response."""
    success: bool
    message: str


@router.post("/test-model", response_model=TestModelResponse)
async def test_model(request: TestModelRequest) -> TestModelResponse:
    """Test if a model/provider combination works."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    
    try:
        from backend.llm.litellm_service import format_model_name, call_llm
        
        # Format model name
        formatted_model = format_model_name(request.provider, request.model)
        
        # Send a tiny, unambiguous test prompt.
        # Don't force tiny token budgets here; some models allocate tokens to reasoning first.
        messages = [{"role": "user", "content": "Reply with exactly: OK"}]

        # Let LiteLLM/provider defaults handle token budgeting; wrapper retries on known param errors.
        response = call_llm(messages, formatted_model)
        
        if response and len(response) > 0:
            return TestModelResponse(
                success=True,
                message=f"Model '{request.model}' works!"
            )
        else:
            return TestModelResponse(
                success=False,
                message=f"Error: Model '{request.model}' returned empty response"
            )
    
    except Exception as e:
        error_msg = str(e)
        # Extract meaningful error message
        if "LLM call failed" in error_msg:
            error_msg = error_msg.replace("LLM call failed: ", "")
        # Keep it simple - just show the error
        return TestModelResponse(
            success=False,
            message=f"Error with {request.model}: {error_msg}"
        )
