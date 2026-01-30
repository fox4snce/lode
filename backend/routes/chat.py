"""
Chat API routes for RAG chat feature (Pro only).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import queue

from backend.feature_flags import is_feature_enabled
from backend.llm.litellm_service import call_llm, call_llm_stream, get_available_providers
from backend.chat.query_improver import improve_query_for_search
from backend.chat.context_manager import filter_results_by_quality, format_context_for_llm
from backend.chat.history_manager import apply_sliding_window
from backend.vectordb.service import search_phrases
from backend.db import check_database_initialized, get_db_connection
from backend.chat import storage as chat_storage

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    """Chat completion request."""
    query: str
    model: str  # e.g., "openai/gpt-4o"
    provider: Optional[str] = None  # UI provider (openai/anthropic/lmstudio/ollama/custom)
    model_name: Optional[str] = None  # raw model input from UI (without provider prefix)
    history: List[ChatMessage] = []
    context_window_size: int = Field(4000, ge=1, le=100_000)  # tokens (up to 100k)
    min_similarity: float = 0.5
    max_context_chunks: int = 5
    include_debug: bool = False


class ChatResponse(BaseModel):
    """Chat completion response."""
    response: str
    improved_query: str
    context_chunks_used: int
    similarity_scores: List[float]
    # Sources (always included when context is used, for clickable links)
    sources: Optional[List[Dict[str, Any]]] = None
    # Optional debug fields (populated when include_debug=True)
    context_preview: Optional[str] = None
    sources_preview: Optional[List[Dict[str, Any]]] = None


def _dedupe_query_list(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for s in items:
        ss = (s or "").strip()
        if not ss:
            continue
        if ss in seen:
            continue
        seen.add(ss)
        out.append(ss)
    return out


async def search_vectordb(queries: List[str], max_chunks: int) -> List[Dict[str, Any]]:
    """
    Search vector database (async wrapper).

    Uses multiple queries (e.g. improved + raw) and merges/dedupes results.
    """
    queries = _dedupe_query_list(queries)
    if not queries:
        return []

    loop = asyncio.get_event_loop()
    grouped = await loop.run_in_executor(
        None,
        lambda: search_phrases(
            phrases=queries,
            top_k=max_chunks * 3,  # Get more candidates for filtering/merging
            min_similarity=None,  # Filter later
            filters={"type": "chunk"},
            include_content=True,
        )
    )
    
    # Merge/dedupe across phrases (keep best similarity per source)
    best: Dict[Any, Dict[str, Any]] = {}
    for group in (grouped or []):
        for r in (group.get("results") or []):
            src = r.get("source") or {}
            md = r.get("metadata") or {}
            key = (
                src.get("conversation_id") or md.get("conversation_id"),
                src.get("chunk_index") or md.get("chunk_index"),
                md.get("type"),
                r.get("content"),
            )
            prev = best.get(key)
            if prev is None or float(r.get("similarity", 0.0)) > float(prev.get("similarity", 0.0)):
                best[key] = r

    merged = sorted(best.values(), key=lambda x: float(x.get("similarity", 0.0)), reverse=True)
    return merged


@router.post("/completion", response_model=ChatResponse)
async def chat_completion(request: ChatRequest) -> ChatResponse:
    """Main chat completion endpoint."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    
    try:
        # Convert history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]

        # Use a windowed subset for query improvement (keeps it relevant + bounded)
        history_for_improvement = apply_sliding_window(history, max_tokens=min(800, request.context_window_size))
        
        # 1. Improve query
        improved_query = improve_query_for_search(
            request.query,
            request.model,
            history_for_improvement
        )
        
        # 2. Search vector database (use both improved + raw, merge results)
        search_results = await search_vectordb(
            [improved_query, request.query],
            request.max_context_chunks,
        )
        
        # 3. Filter by quality
        filtered = filter_results_by_quality(
            search_results,
            request.min_similarity,
            request.max_context_chunks
        )
        
        # 4. Format context
        # Scale RAG context budget with the user's chosen history window (up to ~400k chars for 100k tokens).
        rag_budget_chars = max(6000, min(400_000, int(request.context_window_size) * 4))
        per_chunk_chars = max(800, min(8000, rag_budget_chars // max(1, request.max_context_chunks)))
        context = format_context_for_llm(filtered, max_context_length=rag_budget_chars, max_chunk_chars=per_chunk_chars)
        has_context = len(filtered) > 0
        
        # 5. Apply sliding window to history
        windowed_history = apply_sliding_window(
            history,
            request.context_window_size
        )
        
        # 6. Build messages for LLM
        if has_context:
            # RAG mode: Answer based on context
            system_prompt = (
                "You are a helpful assistant that answers questions based on the provided context. "
                "Use the context information to provide accurate and relevant answers. "
                "If the context doesn't contain relevant information, say so clearly. "
                "Cite sources when referencing specific information from the context."
            )
            user_message = f"""Context information:

{context}

---

User question: {request.query}

Please provide a helpful answer based on the context above."""
        else:
            # No context: Answer from general knowledge
            system_prompt = (
                "You are a helpful assistant that answers questions. "
                "Provide accurate and helpful information based on your knowledge."
            )
            user_message = request.query
        
        # Ensure system message is first
        if not windowed_history or windowed_history[0].get("role") != "system":
            windowed_history.insert(0, {"role": "system", "content": system_prompt})
        else:
            windowed_history[0]["content"] = system_prompt
        
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

        # Persist last-used model/provider (sanity check DB init, but it should be initialized for this page)
        if check_database_initialized():
            try:
                provider = request.provider
                model_name = request.model_name
                if not provider or not model_name:
                    # Parse from formatted model string as fallback
                    if "/" in request.model:
                        provider, model_name = request.model.split("/", 1)
                    else:
                        provider, model_name = "custom", request.model
                conn = get_db_connection()
                chat_storage.set_last_used(conn, provider, model_name)
                conn.close()
            except Exception:
                pass
        
        # Build sources list (always include when context is used)
        sources = None
        if has_context and filtered:
            sources = [
                {
                    "title": (r.get("metadata") or {}).get("title") or "Untitled",
                    "chunk_index": (r.get("metadata") or {}).get("chunk_index"),
                    "similarity": r.get("similarity"),
                    "conversation_id": (r.get("source") or {}).get("conversation_id") or (r.get("metadata") or {}).get("conversation_id"),
                    "message_ids": (r.get("source") or {}).get("message_ids") or (r.get("metadata") or {}).get("message_ids"),
                }
                for r in filtered
            ]
        
        resp = ChatResponse(
            response=response_text,
            improved_query=improved_query,
            context_chunks_used=len(filtered),
            similarity_scores=[r.get("similarity", 0) for r in filtered],
            sources=sources
        )
        if request.include_debug:
            # Show the *actual* context string being passed (trimmed)
            resp.context_preview = context[:6000]
            resp.sources_preview = [
                {
                    "title": (r.get("metadata") or {}).get("title"),
                    "chunk_index": (r.get("metadata") or {}).get("chunk_index"),
                    "similarity": r.get("similarity"),
                    "conversation_id": (r.get("source") or {}).get("conversation_id") or (r.get("metadata") or {}).get("conversation_id"),
                    "message_ids": (r.get("source") or {}).get("message_ids") or (r.get("metadata") or {}).get("message_ids"),
                }
                for r in filtered[: min(len(filtered), 5)]
            ]
        return resp
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


@router.post("/completion-stream")
async def chat_completion_stream(request: ChatRequest):
    """Streaming chat completion endpoint (Server-Sent Events)."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")

    async def gen():
        try:
            history = [{"role": msg.role, "content": msg.content} for msg in request.history]
            history_for_improvement = apply_sliding_window(history, max_tokens=min(800, request.context_window_size))
            improved_query = improve_query_for_search(request.query, request.model, history_for_improvement)
            search_results = await search_vectordb([improved_query, request.query], request.max_context_chunks)
            filtered = filter_results_by_quality(search_results, request.min_similarity, request.max_context_chunks)
            rag_budget_chars = max(6000, min(400_000, int(request.context_window_size) * 4))
            per_chunk_chars = max(800, min(8000, rag_budget_chars // max(1, request.max_context_chunks)))
            context = format_context_for_llm(filtered, max_context_length=rag_budget_chars, max_chunk_chars=per_chunk_chars)

            # send initial meta
            sources = None
            if len(filtered) > 0:
                sources = [
                    {
                        "title": (r.get("metadata") or {}).get("title") or "Untitled",
                        "chunk_index": (r.get("metadata") or {}).get("chunk_index"),
                        "similarity": r.get("similarity"),
                        "conversation_id": (r.get("source") or {}).get("conversation_id") or (r.get("metadata") or {}).get("conversation_id"),
                        "message_ids": (r.get("source") or {}).get("message_ids") or (r.get("metadata") or {}).get("message_ids"),
                    }
                    for r in filtered
                ]
            
            meta = {
                "type": "meta",
                "improved_query": improved_query,
                "context_chunks_used": len(filtered),
                "similarity_scores": [r.get("similarity", 0) for r in filtered],
                "sources": sources,
            }
            if request.include_debug:
                meta["context_preview"] = context[:6000]
                meta["sources_preview"] = sources[: min(len(sources or []), 5)] if sources else []
            yield f"data: {json.dumps(meta)}\n\n"

            windowed_history = apply_sliding_window(history, request.context_window_size)

            if len(filtered) > 0:
                system_prompt = (
                    "You are a helpful assistant that answers questions based on the provided context. "
                    "Use the context information to provide accurate and relevant answers. "
                    "If the context doesn't contain relevant information, say so clearly. "
                    "Cite sources when referencing specific information from the context."
                )
                user_message = f"""Context information:

{context}

---

User question: {request.query}

Please provide a helpful answer based on the context above."""
            else:
                system_prompt = (
                    "You are a helpful assistant that answers questions. "
                    "Provide accurate and helpful information based on your knowledge."
                )
                user_message = request.query

            if not windowed_history or windowed_history[0].get("role") != "system":
                windowed_history.insert(0, {"role": "system", "content": system_prompt})
            else:
                windowed_history[0]["content"] = system_prompt

            messages = windowed_history + [{"role": "user", "content": user_message}]

            # Stream deltas from LLM in a thread so we don't block the event loop;
            # yielding + sleep(0) lets the response flush each chunk to the client.
            sync_queue: queue.Queue = queue.Queue()
            full = []

            def collect_stream():
                for delta in call_llm_stream(messages, request.model, temperature=0.7, max_tokens=2048):
                    full.append(delta)
                    sync_queue.put(delta)
                sync_queue.put(None)  # sentinel

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, collect_stream)

            while True:
                delta = await loop.run_in_executor(None, sync_queue.get)
                if delta is None:
                    break
                yield f"data: {json.dumps({'type':'delta','content':delta})}\n\n"
                await asyncio.sleep(0)  # yield to event loop so chunk can be sent

            final_text = "".join(full)

            # persist last-used model/provider
            if check_database_initialized():
                try:
                    provider = request.provider
                    model_name = request.model_name
                    if not provider or not model_name:
                        if "/" in request.model:
                            provider, model_name = request.model.split("/", 1)
                        else:
                            provider, model_name = "custom", request.model
                    conn = get_db_connection()
                    chat_storage.set_last_used(conn, provider, model_name)
                    conn.close()
                except Exception:
                    pass

            yield f"data: {json.dumps({'type':'done','response':final_text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','error':str(e)})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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
            # Persist verified model + last-used
            if check_database_initialized():
                try:
                    conn = get_db_connection()
                    chat_storage.upsert_verified_model(conn, request.provider, request.model, True)
                    chat_storage.set_last_used(conn, request.provider, request.model)
                    conn.close()
                except Exception:
                    pass
            return TestModelResponse(
                success=True,
                message=f"Model '{request.model}' works!"
            )
        else:
            if check_database_initialized():
                try:
                    conn = get_db_connection()
                    chat_storage.upsert_verified_model(conn, request.provider, request.model, False)
                    conn.close()
                except Exception:
                    pass
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


@router.get("/settings")
async def get_settings():
    """Get persisted chat UI state (last model + verified models + conversation history)."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database is not initialized")
    try:
        conn = get_db_connection()
        settings = chat_storage.get_settings(conn)
        verified = chat_storage.get_verified_models(conn)
        history = chat_storage.load_chat_history(conn)
        conn.close()
        return {"settings": settings, "verified_models": verified, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load chat settings: {str(e)}")


class ChatUISettingsUpdate(BaseModel):
    """Optional UI settings to persist."""
    context_window_size: Optional[int] = None
    min_similarity: Optional[float] = None
    max_context_chunks: Optional[int] = None
    show_debug: Optional[bool] = None


@router.post("/save-settings")
async def save_settings(payload: ChatUISettingsUpdate):
    """Persist chat UI settings (context window, min similarity, max chunks, show debug)."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database is not initialized")
    try:
        ctx = payload.context_window_size
        if ctx is not None:
            ctx = max(1, min(100_000, ctx))
        conn = get_db_connection()
        chat_storage.set_ui_settings(
            conn,
            context_window_size=ctx,
            min_similarity=payload.min_similarity,
            max_context_chunks=payload.max_context_chunks,
            show_debug=payload.show_debug,
        )
        conn.close()
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save chat settings: {str(e)}")


@router.post("/save-history")
async def save_history(request: Request):
    """Save chat conversation history. Accepts both JSON and Blob (for sendBeacon)."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database is not initialized")
    try:
        # Handle both JSON and Blob (from sendBeacon)
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            history = body.get("history", [])
        else:
            # Blob from sendBeacon
            body_bytes = await request.body()
            body = json.loads(body_bytes.decode("utf-8"))
            history = body.get("history", [])
        
        conn = get_db_connection()
        # Ensure history is in the right format (list of {role, content} dicts)
        if history and isinstance(history[0], dict) and "role" in history[0]:
            # Already in correct format
            pass
        else:
            # Convert if needed (shouldn't happen, but be defensive)
            history = [{"role": msg.get("role") or (hasattr(msg, "role") and msg.role), "content": msg.get("content") or (hasattr(msg, "content") and msg.content)} for msg in history]
        
        chat_storage.save_chat_history(conn, history)
        conn.close()
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save chat history: {str(e)}")


@router.post("/clear-history")
async def clear_history():
    """Clear chat conversation history."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database is not initialized")
    try:
        conn = get_db_connection()
        chat_storage.clear_chat_history(conn)
        conn.close()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")
