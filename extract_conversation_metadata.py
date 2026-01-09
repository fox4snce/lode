"""
Extract structured metadata from conversations using LLM.

This script processes conversations in batches, uses an LLM to extract
structured metadata, and stores it in the database.
"""

import sqlite3
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai_llm import generate_structured_response
from conversation_metadata_schema import ConversationMetadata

DB_PATH = 'conversations.db'
BATCH_SIZE = 10  # Process conversations in batches
DEFAULT_MODEL = 'gpt-5-nano'
DEFAULT_MAX_WORKERS = 2
DEFAULT_EXPECTED_OUTPUT_TOKENS = 600
DEFAULT_BACKEND = "openai"  # openai | lmstudio
DEFAULT_LMSTUDIO_URL = "http://127.0.0.1:1234/v1"
# With LM Studio context set to ~22k tokens, we can pass a decent chunk of transcript.
# Still cap for speed and to avoid extreme outliers.
DEFAULT_LMSTUDIO_MAX_CHARS = 60_000
DEFAULT_LMSTUDIO_MAX_CHARS_PER_MESSAGE = 2_000
# Approximate LM Studio context token budget (user set to ~22k). Keep headroom.
DEFAULT_LMSTUDIO_CONTEXT_TOKENS = 22_000

# Instructions passed via the Responses API "instructions" field (counts toward billed input tokens).
LLM_EXTRACTION_INSTRUCTIONS = (
    "Extract only the most important metadata. Keep it concise. "
    "Return only valid JSON matching the schema."
)


def get_conversation_messages(conn: sqlite3.Connection, conversation_id: str) -> List[Dict]:
    """Get all messages for a conversation in chronological order."""
    cursor = conn.execute('''
        SELECT 
            m.message_id,
            m.role,
            m.content,
            m.create_time,
            c.ai_source
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.conversation_id
        WHERE m.conversation_id = ?
        ORDER BY m.create_time ASC, m.id ASC
    ''', (conversation_id,))
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'message_id': row[0],
            'role': row[1],
            'content': row[2],
            'create_time': row[3],
            'ai_source': row[4] if len(row) > 4 else 'gpt'
        })
    
    return messages


def format_conversation_for_llm(messages: List[Dict], max_chars: Optional[int] = None) -> str:
    """
    Format conversation messages into a string for the LLM.
    If conversation is too long, truncate intelligently.
    """
    formatted = []
    total_chars = 0
    
    for msg in messages:
        role = msg['role']
        content = msg['content']
        msg_id = msg['message_id']
        
        # Format: [role] (msg_id): content
        line = f"[{role}] ({msg_id}): {content}\n"
        
        if max_chars is not None and total_chars + len(line) > max_chars:
            # Add a note that conversation was truncated
            formatted.append(f"\n[TRUNCATED - conversation has {len(messages)} total messages]\n")
            break
        
        formatted.append(line)
        total_chars += len(line)
    
    return "".join(formatted)


def format_conversation_for_lmstudio(
    messages: List[Dict],
    max_total_chars: int,
    max_chars_per_message: int,
) -> str:
    """
    LM Studio models often have smaller context windows than OpenAI models.
    We cap the total transcript AND cap each message so a single huge message
    doesn't crowd out everything else (or trigger placeholder-only truncation).
    """
    formatted: List[str] = []
    total_chars = 0

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content") or ""
        msg_id = msg.get("message_id", "")

        # cap per-message content
        if len(content) > max_chars_per_message:
            content = content[:max_chars_per_message] + " ...[truncated]"

        line = f"[{role}] ({msg_id}): {content}\n"

        # If this single line would exceed max_total_chars, include a clipped version
        # rather than emitting only a placeholder.
        remaining = max_total_chars - total_chars
        if remaining <= 0:
            formatted.append(f"\n[TRUNCATED - conversation has {len(messages)} total messages]\n")
            break

        if len(line) > remaining:
            # keep as much as we can (ensure we include *some* transcript)
            clipped = line[: max(0, remaining - 80)]
            formatted.append(clipped)
            formatted.append(f"\n[TRUNCATED - conversation has {len(messages)} total messages]\n")
            break

        formatted.append(line)
        total_chars += len(line)

    return "".join(formatted)


def create_extraction_prompt(conversation_text: str, conversation_id: str) -> str:
    """Create the prompt for metadata extraction."""
    return f"""Extract structured metadata from this conversation. BE CONCISE - focus on the most important items only.

Conversation ID: {conversation_id}

CONVERSATION:
{conversation_text}

REQUIREMENTS - RESPECT THESE LIMITS:
- Topics: Maximum 8 most important topics
- Keywords: Maximum 12 most relevant keywords
- Projects: Maximum 5 projects (only if clearly discussed)
- Entities: Maximum 10 entities (only notable ones)

INSTRUCTIONS:
- Keep everything SHORT and focused - extract only the most important/notable items
- Normalize topics and keywords (no duplicates, clear names)
- Skip minor mentions - only include if truly relevant
- Return ONLY valid JSON matching the schema - no prose, markdown, or commentary
- Keep descriptions brief (max lengths enforced by schema)

Return the structured JSON object now."""


def _is_context_length_error(err: object) -> bool:
    s = str(err).lower()
    return ("context_length_exceeded" in s) or ("context window" in s)


# Keep chunk requests comfortably below any real context limit + schema overhead.
DEFAULT_CHUNK_TOKEN_BUDGET = 80_000


def chunk_messages(messages: List[Dict], max_tokens_per_chunk: int) -> List[List[Dict]]:
    """
    Split messages into chunks that fit within token limit.
    Uses overlap between chunks to maintain context.
    Actually counts tokens to ensure chunks fit.
    """
    from openai_llm import count_tokens
    
    chunks = []
    current_chunk = []
    current_chunk_text = ""
    overlap_size = max(5, len(messages) // 20)  # Overlap ~5% of messages, min 5
    
    # Reserve tokens for prompt + instructions + structured output overhead.
    # We don't perfectly model schema tokenization, so keep headroom.
    prompt_overhead = 2_000
    usable_tokens = max(1_000, max_tokens_per_chunk - prompt_overhead)
    
    for i, msg in enumerate(messages):
        msg_text = f"[{msg['role']}] ({msg['message_id']}): {msg['content']}\n"
        
        # Count tokens for current chunk + this message
        test_text = current_chunk_text + msg_text
        test_tokens = count_tokens(test_text)
        
        # If adding this message would exceed limit, start a new chunk
        if current_chunk and test_tokens > usable_tokens:
            chunks.append(current_chunk)
            
            # Start new chunk with overlap from previous chunk
            overlap_start = max(0, len(current_chunk) - overlap_size)
            current_chunk = current_chunk[overlap_start:]
            
            # Rebuild text for overlap chunk
            current_chunk_text = ""
            for m in current_chunk:
                current_chunk_text += f"[{m['role']}] ({m['message_id']}): {m['content']}\n"
        
        # Add message to current chunk
        current_chunk.append(msg)
        current_chunk_text += msg_text
        
        # Safety check: if single message exceeds limit, we have a problem
        msg_tokens = count_tokens(msg_text)
        if msg_tokens > usable_tokens:
            print(f"      Warning: Single message has ~{msg_tokens:,} tokens (exceeds usable ~{usable_tokens:,})")
            # Include it anyway - extract_metadata_chunked will split further and/or fail fast.
    
    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def merge_metadata_chunks(metadata_chunks: List[ConversationMetadata]) -> ConversationMetadata:
    """
    Merge metadata from multiple chunks into a single metadata object.
    Combines lists (topics, keywords, etc.), takes most confident scores, etc.
    """
    if not metadata_chunks:
        raise ValueError("Cannot merge empty metadata chunks")
    
    if len(metadata_chunks) == 1:
        return metadata_chunks[0]
    
    # Start with the first chunk as base
    merged = metadata_chunks[0].model_copy(deep=True)
    
    # Merge topics (deduplicate, keep unique)
    all_topics = set(merged.topics)
    for chunk in metadata_chunks[1:]:
        all_topics.update(chunk.topics)
    merged.topics = sorted(list(all_topics))[:8]  # Limit to 8 as per schema
    
    # Merge keywords (deduplicate, keep unique)
    all_keywords = set(merged.keywords)
    for chunk in metadata_chunks[1:]:
        all_keywords.update(chunk.keywords)
    merged.keywords = sorted(list(all_keywords))[:12]  # Limit to 12 as per schema
    
    # Merge conversation types (deduplicate)
    all_types = set(merged.conversation_types)
    for chunk in metadata_chunks[1:]:
        all_types.update(chunk.conversation_types)
    merged.conversation_types = sorted(list(all_types))
    
    # Merge intents (deduplicate)
    all_intents = set(merged.intents)
    for chunk in metadata_chunks[1:]:
        all_intents.update(chunk.intents)
    merged.intents = sorted(list(all_intents))
    
    # Merge project candidates (deduplicate by name)
    project_map = {p.name: p for p in merged.project_candidates}
    for chunk in metadata_chunks[1:]:
        for project in chunk.project_candidates:
            if project.name not in project_map:
                project_map[project.name] = project
            else:
                # Keep the one with longer description (more detailed)
                if len(project.description) > len(project_map[project.name].description):
                    project_map[project.name] = project
    merged.project_candidates = list(project_map.values())[:5]  # Limit to 5 as per schema
    
    # Take the longest summary (most comprehensive)
    longest_summary = max(metadata_chunks, key=lambda m: len(m.summary)).summary
    merged.summary = longest_summary
    
    # Take the first non-empty title, or longest if all have titles
    titles = [m.title for m in metadata_chunks if m.title]
    if titles:
        merged.title = max(titles, key=len) if all(titles) else titles[0]
    
    # Take the first non-empty one_liner, or most descriptive
    one_liners = [m.one_liner for m in metadata_chunks if m.one_liner]
    if one_liners:
        merged.one_liner = max(one_liners, key=len) if all(one_liners) else one_liners[0]
    
    # Take the highest confidence score
    merged.classification_confidence = max(m.classification_confidence for m in metadata_chunks)
    merged.confidence_score = max(m.confidence_score for m in metadata_chunks)
    
    # For status, take the one that appears most often, or 'ongoing' if tie
    statuses = [m.status for m in metadata_chunks]
    from collections import Counter
    status_counts = Counter(statuses)
    merged.status = status_counts.most_common(1)[0][0] if status_counts else 'unclear'
    
    # Update schema version to indicate it was merged
    merged.schema_version = f"{merged.schema_version}_merged_{len(metadata_chunks)}chunks"
    
    return merged


def extract_metadata_chunked(
    conversation_id: str,
    messages: List[Dict],
    model: str,
    max_tokens_per_chunk: int
) -> tuple[ConversationMetadata, Optional[dict]]:
    """
    Extract metadata from a long conversation by chunking it.
    Processes each chunk separately, then merges the results.
    """
    from openai_llm import count_tokens
    
    # Never try to run a single "chunk" near the model limit; keep chunks smaller and merge.
    token_budget = min(max_tokens_per_chunk, DEFAULT_CHUNK_TOKEN_BUDGET)

    # Split messages into chunks
    chunks = chunk_messages(messages, token_budget)
    print(f"    Split into {len(chunks)} chunks (budget ~{token_budget:,} tokens each)")

    metadata_chunks: List[ConversationMetadata] = []
    total_usage_input = 0
    total_usage_output = 0

    def _accumulate_usage(u: Optional[object]) -> None:
        nonlocal total_usage_input, total_usage_output
        if not u:
            return
        # Responses API usage usually has input_tokens/output_tokens, but keep fallbacks.
        for attr in ("input_tokens", "prompt_tokens"):
            if hasattr(u, attr):
                total_usage_input += int(getattr(u, attr) or 0)
                break
        for attr in ("output_tokens", "completion_tokens"):
            if hasattr(u, attr):
                total_usage_output += int(getattr(u, attr) or 0)
                break

    def _extract_chunk_recursive(chunk_msgs: List[Dict], chunk_tag: str) -> List[ConversationMetadata]:
        """
        Try extracting metadata for a chunk. If the API still says context too long,
        split the chunk and recurse until it succeeds.
        """
        chunk_text = format_conversation_for_llm(chunk_msgs, max_chars=None)
        est_tokens = count_tokens(chunk_text)
        print(f"      [{chunk_tag}] messages={len(chunk_msgs)} est_tokens~{est_tokens:,}")

        try:
            prompt = create_extraction_prompt(chunk_text, f"{conversation_id}_{chunk_tag}")
            md, u = generate_structured_response(
                prompt,
                ConversationMetadata,
                model=model,
                instructions=LLM_EXTRACTION_INSTRUCTIONS,
            )
            _accumulate_usage(u)
            return [md]
        except Exception as e:
            if _is_context_length_error(e) and len(chunk_msgs) > 1:
                mid = len(chunk_msgs) // 2
                left = chunk_msgs[:mid]
                right = chunk_msgs[mid:]
                print(f"      [{chunk_tag}] context too long -> splitting into {len(left)} + {len(right)} messages")
                out: List[ConversationMetadata] = []
                out.extend(_extract_chunk_recursive(left, f"{chunk_tag}a"))
                out.extend(_extract_chunk_recursive(right, f"{chunk_tag}b"))
                return out
            raise

    # Process each chunk (with recursive split on context errors)
    for i, chunk in enumerate(chunks, 1):
        chunk_tag = f"chunk{i}"
        print(f"    Processing {chunk_tag}/{len(chunks)} ({len(chunk)} messages)...")
        try:
            metadata_chunks.extend(_extract_chunk_recursive(chunk, chunk_tag))
        except Exception as e:
            print(f"    Error processing {chunk_tag}: {e}")
            continue
    
    if not metadata_chunks:
        print(f"    Failed to extract metadata from any chunks")
        return None, None
    
    # Merge metadata from all chunks
    print(f"    Merging metadata from {len(metadata_chunks)} chunks...")
    merged_metadata = merge_metadata_chunks(metadata_chunks)
    merged_metadata.model_used = f"{model}_chunked"
    
    # Create combined usage object
    combined_usage = None
    if total_usage_input > 0 or total_usage_output > 0:
        class Usage:
            def __init__(self, prompt_tokens, completion_tokens):
                self.prompt_tokens = prompt_tokens
                self.completion_tokens = completion_tokens
                self.total_tokens = prompt_tokens + completion_tokens
        combined_usage = Usage(total_usage_input, total_usage_output)
    
    print(f"    Successfully merged metadata from {len(metadata_chunks)} chunks")
    
    return merged_metadata, combined_usage


def extract_metadata_for_conversation(
    conn: sqlite3.Connection,
    conversation_id: str,
    model: str = DEFAULT_MODEL
) -> tuple[Optional[ConversationMetadata], Optional[dict]]:
    """Extract metadata for a single conversation."""
    
    # Get conversation info
    cursor = conn.execute('''
        SELECT title, ai_source
        FROM conversations
        WHERE conversation_id = ?
    ''', (conversation_id,))
    
    row = cursor.fetchone()
    if not row:
        print(f"  Conversation {conversation_id} not found")
        return None, None
    
    title, ai_source = row
    
    # Get messages
    messages = get_conversation_messages(conn, conversation_id)
    if not messages:
        print(f"  No messages found for {conversation_id}")
        return None, None
    
    # Format conversation for LLM
    from openai_llm import count_tokens
    
    # Model context window sizes (leaving headroom for prompt + output)
    # gpt-5-nano: 400k context, leave ~50k for prompt/output overhead
    # gpt-5-mini: 400k context, leave ~50k for prompt/output overhead
    CONTEXT_LIMITS = {
        'gpt-5-nano': 350000,  # 400k - 50k headroom
        'gpt-5-mini': 350000,  # 400k - 50k headroom
    }
    max_input_tokens = CONTEXT_LIMITS.get(model, 300000)  # Default conservative limit
    
    conversation_text = format_conversation_for_llm(messages, max_chars=None)
    input_tokens_estimate = count_tokens(conversation_text)
    
    print(f"    Input: ~{input_tokens_estimate:,} tokens ({len(conversation_text):,} chars, {len(messages)} messages)")
    
    # Check if conversation exceeds context window - if so, chunk it
    if input_tokens_estimate > max_input_tokens:
        print(f"    Conversation too long ({input_tokens_estimate:,} tokens > {max_input_tokens:,} limit)")
        print(f"    Splitting into chunks and processing separately...")
        return extract_metadata_chunked(conversation_id, messages, model, max_input_tokens)
    
    # Create prompt
    prompt = create_extraction_prompt(conversation_text, conversation_id)
    
    # Use structured output to extract metadata
    try:
        metadata, usage = generate_structured_response(
            prompt,
            ConversationMetadata,
            model=model,
            instructions=LLM_EXTRACTION_INSTRUCTIONS
        )
        
        # Set model_used in metadata
        metadata.model_used = model
        
        return metadata, usage
        
    except Exception as e:
        error_str = str(e)
        # Check if it's a context length error - try chunking as fallback
        if 'context_length_exceeded' in error_str or 'context window' in error_str.lower():
            print(f"    Context window error detected, falling back to chunking...")
            return extract_metadata_chunked(conversation_id, messages, model, max_input_tokens)
        print(f"  Error extracting metadata: {e}")
        return None, None


def _extract_metadata_task(
    db_path: str,
    conversation_id: str,
    model: str,
) -> Dict:
    """
    Worker task: open its own SQLite connection (thread-safe), extract metadata, and return
    structured result for the main thread to log + store.
    """
    import time
    from openai_llm import count_tokens

    t0 = time.time()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        messages = get_conversation_messages(conn, conversation_id)
        
        # Model context window sizes (leaving headroom for prompt + output)
        CONTEXT_LIMITS = {
            'gpt-5-nano': 350000,  # 400k - 50k headroom
            'gpt-5-mini': 350000,  # 400k - 50k headroom
        }
        max_input_tokens = CONTEXT_LIMITS.get(model, 300000)  # Default conservative limit
        
        conversation_text = format_conversation_for_llm(messages, max_chars=None)
        input_tokens_estimate = count_tokens(conversation_text)
        
        # Check if conversation exceeds context window - if so, chunk it
        if input_tokens_estimate > max_input_tokens:
            # Use chunking approach
            metadata, usage = extract_metadata_chunked(conversation_id, messages, model, max_input_tokens)
        else:
            # Normal processing
            prompt = create_extraction_prompt(conversation_text, conversation_id)
            metadata, usage = generate_structured_response(
                prompt,
                ConversationMetadata,
                model=model,
                instructions=LLM_EXTRACTION_INSTRUCTIONS,
            )
            metadata.model_used = model

        if metadata is None:
            return {
                "conversation_id": conversation_id,
                "ok": False,
                "error": "Failed to extract metadata",
                "elapsed_s": time.time() - t0,
            }

        return {
            "conversation_id": conversation_id,
            "ok": True,
            "metadata": metadata,
            "usage": usage,
            "input_tokens_estimate": input_tokens_estimate,
            "chars": len(conversation_text),
            "messages": len(messages),
            "elapsed_s": time.time() - t0,
        }
    except Exception as e:
        error_str = str(e)
        # Check if it's a context length error - try chunking as fallback
        if 'context_length_exceeded' in error_str or 'context window' in error_str.lower():
            try:
                metadata, usage = extract_metadata_chunked(conversation_id, messages, model, max_input_tokens)
                if metadata:
                    return {
                        "conversation_id": conversation_id,
                        "ok": True,
                        "metadata": metadata,
                        "usage": usage,
                        "input_tokens_estimate": 0,
                        "chars": 0,
                        "messages": len(messages),
                        "elapsed_s": time.time() - t0,
                    }
            except:
                pass  # Fall through to error return
        return {
            "conversation_id": conversation_id,
            "ok": False,
            "error": str(e),
            "elapsed_s": time.time() - t0,
        }
    finally:
        conn.close()


def _extract_metadata_via_lmstudio(
    conversation_text: str,
    conversation_id: str,
    lmstudio_url: str,
    stream: bool,
    temperature: float = 0.2,
) -> ConversationMetadata:
    """
    Local backend (LM Studio) does NOT support Structured Outputs.
    We embed the JSON schema in the prompt and then validate the returned JSON with Pydantic.
    """
    from lmstudio_llm import chat_completions, extract_json_object, unwrap_common_wrapper

    def _coerce_dict_for_schema(raw: object) -> dict:
        """
        Best-effort coercion for local models that don't follow the schema strictly.
        We salvage what we can and fill missing required fields with safe defaults
        so the pipeline can keep moving.
        """
        if not isinstance(raw, dict):
            return {}

        # unwrap common nested wrappers
        raw = unwrap_common_wrapper(raw)
        if isinstance(raw, dict) and "response" in raw and isinstance(raw["response"], dict):
            raw = raw["response"]

        out: dict = {}

        # Some models emit a list of {"key": ..., "value": ...} pairs under "elements"
        if isinstance(raw, dict) and isinstance(raw.get("elements"), list):
            for item in raw["elements"]:
                if isinstance(item, dict) and "key" in item and "value" in item:
                    k = str(item["key"])
                    out[k] = item["value"]

        # merge direct keys as well
        if isinstance(raw, dict):
            for k, v in raw.items():
                if k == "elements":
                    continue
                out[k] = v

        # required keys / defaults
        defaults = {
            "title": "",
            "summary": "",
            "one_liner": None,
            "conversation_types": [],
            "intents": [],
            "status": "unclear",
            "classification_confidence": 0.5,
            "topics": [],
            "keywords": [],
            "project_candidates": [],
            "schema_version": "1.0",
            "model_used": "lmstudio",
            "confidence_score": 0.5,
        }

        # try alternate fields for title/summary if missing
        if not out.get("title") and out.get("name"):
            out["title"] = out.get("name")
        if not out.get("summary") and out.get("description"):
            out["summary"] = out.get("description")

        # coerce numeric fields
        def _to_float01(x, default=0.5) -> float:
            if isinstance(x, (int, float)):
                val = float(x)
            elif isinstance(x, str):
                s = x.strip().lower()
                if s in ("high", "very_high"):
                    val = 0.85
                elif s in ("medium", "med"):
                    val = 0.6
                elif s in ("low", "very_low"):
                    val = 0.35
                else:
                    try:
                        val = float(s)
                    except Exception:
                        val = default
            else:
                val = default
            if val < 0.0:
                val = 0.0
            if val > 1.0:
                val = 1.0
            return val

        out["classification_confidence"] = _to_float01(out.get("classification_confidence", defaults["classification_confidence"]))
        out["confidence_score"] = _to_float01(out.get("confidence_score", defaults["confidence_score"]))

        # list fields
        def _to_str_list(x) -> list:
            if x is None:
                return []
            if isinstance(x, list):
                return [str(i) for i in x if str(i).strip()]
            if isinstance(x, str):
                s = x.strip()
                # try json list
                if s.startswith("[") and s.endswith("]"):
                    try:
                        arr = json.loads(s)
                        if isinstance(arr, list):
                            return [str(i) for i in arr if str(i).strip()]
                    except Exception:
                        pass
                # comma/semicolon split
                parts = [p.strip() for p in s.replace(";", ",").split(",")]
                return [p for p in parts if p]
            return [str(x)]

        out["conversation_types"] = _to_str_list(out.get("conversation_types", defaults["conversation_types"]))
        out["intents"] = _to_str_list(out.get("intents", defaults["intents"]))
        out["topics"] = _to_str_list(out.get("topics", defaults["topics"]))[:8]
        out["keywords"] = _to_str_list(out.get("keywords", defaults["keywords"]))[:12]

        # status
        if not isinstance(out.get("status"), str) or not out.get("status"):
            out["status"] = defaults["status"]

        # one_liner
        if out.get("one_liner") is not None and not isinstance(out.get("one_liner"), str):
            out["one_liner"] = str(out.get("one_liner"))

        # title/summary as strings
        out["title"] = str(out.get("title") or defaults["title"])
        out["summary"] = str(out.get("summary") or defaults["summary"])

        # project_candidates (keep empty unless already a list of dicts)
        pc = out.get("project_candidates", defaults["project_candidates"])
        if not isinstance(pc, list):
            pc = []
        out["project_candidates"] = pc

        # fill any missing required keys
        for k, v in defaults.items():
            if k not in out or out[k] is None and v is not None:
                out[k] = v

        # remove unknown top-level keys (strict)
        allowed = set(defaults.keys())
        out = {k: out[k] for k in defaults.keys()}
        return out

    # Give the local model a compact, explicit contract + an example to follow.
    # IMPORTANT: Do NOT embed the full JSON Schema; many local models run with ~4k context.
    fields = list(ConversationMetadata.model_fields.keys())

    example = {
        "title": "Short title",
        "summary": "One paragraph summary.",
        "one_liner": None,
        "conversation_types": ["analysis"],
        "intents": ["analyze"],
        "status": "ongoing",
        "classification_confidence": 0.5,
        "topics": ["Topic A"],
        "keywords": ["keyword"],
        "project_candidates": [],
        "schema_version": "1.0",
        "model_used": "lmstudio",
        "confidence_score": 0.5,
    }
    example_str = json.dumps(example, ensure_ascii=True)

    # Ultra-compact type/size contract (kept small for local context limits)
    contract = (
        "Contract:\n"
        "- Return ONLY a single JSON object (no markdown/code fences, no wrapper keys).\n"
        "- MUST include ALL required keys; NO extra keys.\n"
        "- title: string <=120 chars\n"
        "- summary: string <=800 chars\n"
        "- one_liner: string <=120 chars OR null\n"
        "- conversation_types: array of strings (<=5 items)\n"
        "- intents: array of strings (<=5 items)\n"
        "- status: one of [resolved, ongoing, abandoned, unclear]\n"
        "- classification_confidence: number 0..1\n"
        "- topics: array of strings (<=8 items)\n"
        "- keywords: array of strings (<=12 items)\n"
        "- project_candidates: array (<=5 items), usually []\n"
        "- schema_version: string (use \"1.0\")\n"
        "- model_used: string (use \"lmstudio\")\n"
        "- confidence_score: number 0..1\n"
    )

    system = (
        "You are a metadata extractor. Return ONLY a single JSON object.\n"
        "Do NOT wrap it in any outer key (no {\"response\": ...}).\n"
        "Do NOT use markdown or code fences.\n"
        "All required keys must be present and types must match.\n"
    )
    user = (
        "Return a JSON object with EXACTLY these top-level keys (no extras):\n"
        + ", ".join(fields)
        + "\n\n"
        f"{contract}\n"
        "Example shape (values are examples only):\n"
        f"{example_str}\n\n"
        f"Conversation ID: {conversation_id}\n\n"
        "Conversation transcript:\n"
        f"{conversation_text}\n"
    )

    last_err: Optional[str] = None
    last_text: Optional[str] = None

    for attempt in range(1, 3):
        text = chat_completions(
            base_url=lmstudio_url,
            model=None,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=-1,
            stream=stream,
            print_stream=stream,
        )
        last_text = text

        try:
            obj_text = extract_json_object(text)
            data = json.loads(obj_text)
            data = _coerce_dict_for_schema(data)
            return ConversationMetadata.model_validate(data)
        except Exception as e:
            last_err = str(e)
            # If the local model complains about context length, retry with a shorter transcript.
            if ("context length" in last_err.lower() or "context" in last_err.lower()) and len(conversation_text) > 1000:
                conversation_text = conversation_text[: max(1000, len(conversation_text) // 2)]
                user = (
                    "Return a JSON object with EXACTLY these top-level keys (no extras):\n"
                    + ", ".join(fields)
                    + "\n\n"
                    f"{contract}\n"
                    "Example shape (values are examples only):\n"
                    f"{example_str}\n\n"
                    f"Conversation ID: {conversation_id}\n\n"
                    "Conversation transcript:\n"
                    f"{conversation_text}\n"
                )
            # Retry once with a "repair" prompt using the model's prior output
            if attempt == 1:
                repair_system = (
                    "Fix invalid JSON into valid JSON that matches the provided schema exactly. "
                    "Return ONLY the JSON object. No markdown."
                )
                repair_user = (
                    "Required top-level keys (no extras):\n"
                    + ", ".join(fields)
                    + "\n\n"
                    + contract
                    + "\n\nBad output to fix:\n"
                    + (obj_text if 'obj_text' in locals() else (text or ""))
                    + "\n\nError:\n"
                    + last_err
                )
                text = chat_completions(
                    base_url=lmstudio_url,
                    model=None,
                    messages=[
                        {"role": "system", "content": repair_system},
                        {"role": "user", "content": repair_user},
                    ],
                    temperature=0.0,
                    max_tokens=-1,
                    stream=stream,
                    print_stream=stream,
                )
                last_text = text
                # loop continues to validate
            else:
                break

    raise ValueError(f"LM Studio output did not validate. Last error: {last_err}. Last text: {last_text[:500] if last_text else ''}")


def extract_metadata_lmstudio_chunked(
    conversation_id: str,
    messages: List[Dict],
    lmstudio_url: str,
    stream: bool,
) -> ConversationMetadata:
    """
    Chunk long conversations for LM Studio (smaller context than OpenAI), run extraction
    per chunk, then merge results so we don't lose topics/keywords/etc.
    """
    # Pre-truncate per-message so a single huge message can't blow up token counting or context.
    msgs = []
    for m in messages:
        mm = dict(m)
        c = (mm.get("content") or "")
        if len(c) > DEFAULT_LMSTUDIO_MAX_CHARS_PER_MESSAGE:
            mm["content"] = c[:DEFAULT_LMSTUDIO_MAX_CHARS_PER_MESSAGE] + " ...[truncated]"
        msgs.append(mm)

    chunks = chunk_messages(msgs, DEFAULT_LMSTUDIO_CONTEXT_TOKENS)
    md_chunks: List[ConversationMetadata] = []
    for i, ch in enumerate(chunks, 1):
        ch_text = format_conversation_for_lmstudio(
            ch,
            max_total_chars=DEFAULT_LMSTUDIO_MAX_CHARS,
            max_chars_per_message=DEFAULT_LMSTUDIO_MAX_CHARS_PER_MESSAGE,
        )
        md = _extract_metadata_via_lmstudio(
            conversation_text=ch_text,
            conversation_id=f"{conversation_id}_chunk{i}",
            lmstudio_url=lmstudio_url,
            stream=stream,
        )
        md.model_used = "lmstudio"
        md_chunks.append(md)

    merged = merge_metadata_chunks(md_chunks)
    merged.model_used = "lmstudio_chunked"
    return merged


def store_metadata(conn: sqlite3.Connection, conversation_id: str, metadata: ConversationMetadata):
    """Store metadata in the database."""
    cursor = conn.cursor()
    
    # Convert metadata to JSON
    metadata_dict = metadata.model_dump()
    metadata_json = json.dumps(metadata_dict)
    
    # Store in main metadata table
    cursor.execute('''
        INSERT OR REPLACE INTO conversation_metadata 
        (conversation_id, metadata_json, schema_version, model_used, confidence_score, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        conversation_id,
        metadata_json,
        metadata.schema_version,
        metadata.model_used,
        metadata.confidence_score
    ))
    
    # Store indexed fields for fast queries
    # Delete old indexed fields for this conversation
    cursor.execute('DELETE FROM conversation_metadata_indexed WHERE conversation_id = ?', (conversation_id,))
    
    # Index topics
    for topic in metadata.topics:
        cursor.execute('''
            INSERT OR IGNORE INTO conversation_metadata_indexed 
            (conversation_id, field_type, field_name, field_value)
            VALUES (?, 'topic', 'topic', ?)
        ''', (conversation_id, topic))
    
    # Index keywords
    for keyword in metadata.keywords:
        cursor.execute('''
            INSERT OR IGNORE INTO conversation_metadata_indexed 
            (conversation_id, field_type, field_name, field_value)
            VALUES (?, 'keyword', 'keyword', ?)
        ''', (conversation_id, keyword))
    
    # Index conversation types
    for conv_type in metadata.conversation_types:
        cursor.execute('''
            INSERT OR IGNORE INTO conversation_metadata_indexed 
            (conversation_id, field_type, field_name, field_value)
            VALUES (?, 'conversation_type', 'type', ?)
        ''', (conversation_id, conv_type))
    
    # Index intents
    for intent in metadata.intents:
        cursor.execute('''
            INSERT OR IGNORE INTO conversation_metadata_indexed 
            (conversation_id, field_type, field_name, field_value)
            VALUES (?, 'intent', 'intent', ?)
        ''', (conversation_id, intent))
    
    # Index status
    cursor.execute('''
        INSERT OR IGNORE INTO conversation_metadata_indexed 
        (conversation_id, field_type, field_name, field_value)
        VALUES (?, 'status', 'status', ?)
    ''', (conversation_id, metadata.status))
    
    # Index projects
    for project in metadata.project_candidates:
        msg_ids = ','.join([e.message_id for e in project.evidence])
        cursor.execute('''
            INSERT OR IGNORE INTO conversation_metadata_indexed 
            (conversation_id, field_type, field_name, field_value, evidence_message_ids)
            VALUES (?, 'project', ?, ?, ?)
        ''', (conversation_id, project.name, project.description, msg_ids))
    
    conn.commit()


def process_conversations(
    db_path: str = DB_PATH,
    batch_size: int = BATCH_SIZE,
    model: str = DEFAULT_MODEL,
    conversation_id: Optional[str] = None,
    force_regenerate: bool = False,
    limit: Optional[int] = None,
    print_llm_response: bool = False,
    max_workers: int = DEFAULT_MAX_WORKERS,
    dry_run: bool = False,
    expected_output_tokens: int = DEFAULT_EXPECTED_OUTPUT_TOKENS,
    backend: str = DEFAULT_BACKEND,
    lmstudio_url: str = DEFAULT_LMSTUDIO_URL,
    lmstudio_stream: bool = True,
):
    """
    Process conversations to extract metadata.
    
    Args:
        db_path: Path to database
        batch_size: Number of conversations to process in each batch
        model: LLM model to use
        conversation_id: Optional specific conversation ID to process
        force_regenerate: If True, regenerate metadata even if it exists
    """
    """
    Process conversations to extract metadata.
    
    Args:
        db_path: Path to database
        batch_size: Number of conversations to process in each batch
        model: LLM model to use
        conversation_id: Optional specific conversation ID to process
        force_regenerate: If True, regenerate metadata even if it exists
    """
    def _safe_print(s: str) -> None:
        """
        Windows consoles (cp1252) can crash on some Unicode characters. Print with a
        fallback that escapes unsupported codepoints.
        """
        try:
            print(s)
        except UnicodeEncodeError:
            safe = s.encode("ascii", errors="backslashreplace").decode("ascii", errors="ignore")
            print(safe)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get list of conversations to process
    if conversation_id:
        # Check if metadata already exists (unless forcing regeneration)
        if not force_regenerate:
            cursor = conn.execute('''
                SELECT conversation_id FROM conversation_metadata WHERE conversation_id = ?
            ''', (conversation_id,))
            if cursor.fetchone():
                print(f"Conversation {conversation_id} already has metadata. Use --force to regenerate.")
                conn.close()
                return
        
        cursor = conn.execute('''
            SELECT conversation_id, title
            FROM conversations
            WHERE conversation_id = ?
        ''', (conversation_id,))
    else:
        if force_regenerate:
            cursor = conn.execute('''
                SELECT conversation_id, title
                FROM conversations
                ORDER BY create_time DESC
            ''')
        else:
            # Only process conversations without metadata
            if limit is not None:
                cursor = conn.execute(
                    '''
                    SELECT c.conversation_id, c.title
                    FROM conversations c
                    LEFT JOIN conversation_metadata m ON c.conversation_id = m.conversation_id
                    WHERE m.conversation_id IS NULL
                    ORDER BY c.create_time DESC
                    LIMIT ?
                    ''',
                    (int(limit),),
                )
            else:
                cursor = conn.execute('''
                    SELECT c.conversation_id, c.title
                    FROM conversations c
                    LEFT JOIN conversation_metadata m ON c.conversation_id = m.conversation_id
                    WHERE m.conversation_id IS NULL
                    ORDER BY c.create_time DESC
                ''')
    
    conversations = cursor.fetchall()
    total = len(conversations)
    
    if total == 0:
        print("No conversations to process.")
        conn.close()
        return
    
    _safe_print(f"Processing {total} conversation(s)...")
    
    processed = 0
    succeeded = 0
    failed = 0
    
    # Token usage tracking
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    
    # Cost per 1M tokens by model (OpenAI backend only)
    MODEL_PRICING_PER_M = {
        "gpt-5-nano": {"input": 0.05, "output": 0.40},
        "gpt-5-mini": {"input": 0.25, "output": 2.00},
    }
    if backend == "openai":
        pricing = MODEL_PRICING_PER_M.get(model)
        if pricing:
            INPUT_COST_PER_M = pricing["input"]
            OUTPUT_COST_PER_M = pricing["output"]
            print(f"Pricing for {model}: ${INPUT_COST_PER_M}/1M input, ${OUTPUT_COST_PER_M}/1M output")
        else:
            INPUT_COST_PER_M = None
            OUTPUT_COST_PER_M = None
            print(f"Pricing unknown for model '{model}'. Cost estimates will be skipped.")
    else:
        INPUT_COST_PER_M = None
        OUTPUT_COST_PER_M = None
        print("Local backend (LM Studio): skipping token pricing/cost estimates.")
    
    import time
    start_time = time.time()

    if dry_run:
        # Estimate cost without calling the LLM.
        # We estimate input tokens for: (prompt + instructions). This ignores any schema overhead.
        from openai_llm import count_tokens

        print("DRY RUN: estimating cost only (no LLM calls, no DB writes).")
        print(f"Assumed output cap: {expected_output_tokens} tokens per conversation")

        if INPUT_COST_PER_M is None or OUTPUT_COST_PER_M is None:
            print("Cannot estimate costs: unknown model pricing.")
            conn.close()
            return

        total_estimated_cost = 0.0
        total_estimated_input_tokens = 0
        total_estimated_output_tokens = 0

        for idx, conv in enumerate(conversations):
            conv_id = conv["conversation_id"]
            title = (conv["title"] or "Untitled")

            messages = get_conversation_messages(conn, conv_id)
            conversation_text = format_conversation_for_llm(messages, max_chars=None)
            prompt = create_extraction_prompt(conversation_text, conv_id)

            prompt_tokens = count_tokens(prompt)
            instructions_tokens = count_tokens(LLM_EXTRACTION_INSTRUCTIONS)
            input_tokens_est = prompt_tokens + instructions_tokens
            output_tokens_est = expected_output_tokens

            cost_est = (input_tokens_est / 1_000_000 * INPUT_COST_PER_M) + (output_tokens_est / 1_000_000 * OUTPUT_COST_PER_M)

            total_estimated_input_tokens += input_tokens_est
            total_estimated_output_tokens += output_tokens_est
            total_estimated_cost += cost_est

            print(
                f"[{idx+1}/{total}] {title[:60]} ({conv_id[:16]}...): "
                f"input~{input_tokens_est:,} (prompt~{prompt_tokens:,}+instr~{instructions_tokens:,}), "
                f"output~{output_tokens_est:,} => ${cost_est:.4f}"
            )

        total_elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print("DRY RUN COMPLETE")
        print(f"{'='*70}")
        print(f"  Conversations: {total}")
        print(f"  Estimated input tokens: {total_estimated_input_tokens:,}")
        print(f"  Estimated output tokens: {total_estimated_output_tokens:,}")
        print(f"  Estimated total tokens: {total_estimated_input_tokens + total_estimated_output_tokens:,}")
        print(f"  Estimated cost: ${total_estimated_cost:.2f}")
        print(f"  Time: {total_elapsed:.1f}s")
        print(f"{'='*70}")
        conn.close()
        return
    
    for i in range(0, total, batch_size):
        batch = conversations[i:i + batch_size]
        _safe_print(f"\n{'='*70}")
        _safe_print(f"Batch {i//batch_size + 1}/{(total-1)//batch_size + 1} (workers={max_workers})")
        _safe_print(f"{'='*70}")

        # Submit tasks for this batch; the executor limits concurrency to max_workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_conv = {}
            for conv in batch:
                conv_id = conv['conversation_id']
                title = conv['title'] or 'Untitled'
                if backend == "openai":
                    future = executor.submit(_extract_metadata_task, db_path, conv_id, model)
                else:
                    # LM Studio backend: do extraction in worker but without token usage.
                    def _lm_task(cid: str) -> Dict:
                        import time
                        from openai_llm import count_tokens
                        t0 = time.time()
                        c = sqlite3.connect(db_path)
                        c.row_factory = sqlite3.Row
                        try:
                            msgs = get_conversation_messages(c, cid)
                            convo_text = format_conversation_for_lmstudio(
                                msgs,
                                max_total_chars=DEFAULT_LMSTUDIO_MAX_CHARS,
                                max_chars_per_message=DEFAULT_LMSTUDIO_MAX_CHARS_PER_MESSAGE,
                            )
                            prompt_tokens_est = count_tokens(convo_text)

                            # If likely too long for LM Studio context, chunk + merge.
                            if prompt_tokens_est > int(DEFAULT_LMSTUDIO_CONTEXT_TOKENS * 0.85):
                                meta = extract_metadata_lmstudio_chunked(
                                    conversation_id=cid,
                                    messages=msgs,
                                    lmstudio_url=lmstudio_url,
                                    stream=lmstudio_stream,
                                )
                            else:
                                meta = _extract_metadata_via_lmstudio(
                                    conversation_text=convo_text,
                                    conversation_id=cid,
                                    lmstudio_url=lmstudio_url,
                                    stream=lmstudio_stream,
                                )
                            meta.model_used = "lmstudio"
                            return {
                                "conversation_id": cid,
                                "ok": True,
                                "metadata": meta,
                                "usage": None,
                                "input_tokens_estimate": prompt_tokens_est,
                                "chars": len(convo_text),
                                "messages": len(msgs),
                                "elapsed_s": time.time() - t0,
                            }
                        except Exception as e:
                            return {"conversation_id": cid, "ok": False, "error": str(e), "elapsed_s": time.time() - t0}
                        finally:
                            c.close()

                    future = executor.submit(_lm_task, conv_id)
                future_to_conv[future] = {
                    "conversation_id": conv_id,
                    "title": title,
                }

            # Consume results as they complete
            for future in as_completed(future_to_conv):
                info = future_to_conv[future]
                conv_id = info["conversation_id"]
                title = info["title"]

                result = future.result()
                conv_elapsed = result.get("elapsed_s", 0.0)

                _safe_print(f"\n[{processed + 1}/{total}] Processing: {title[:60]}")
                _safe_print(f"  Conversation ID: {conv_id[:40]}...")
                if "input_tokens_estimate" in result:
                    print(
                        f"    Input: ~{result['input_tokens_estimate']:,} tokens "
                        f"({result.get('chars', 0):,} chars, {result.get('messages', 0)} messages)"
                    )

                if result.get("ok"):
                    metadata: ConversationMetadata = result["metadata"]
                    usage = result.get("usage")

                    # Store metadata (single thread) to avoid SQLite write contention
                    store_metadata(conn, conv_id, metadata)

                    # Track token usage
                    input_tokens = usage.input_tokens if usage and hasattr(usage, 'input_tokens') else 0
                    output_tokens = usage.output_tokens if usage and hasattr(usage, 'output_tokens') else 0
                    total_tokens = usage.total_tokens if usage and hasattr(usage, 'total_tokens') else (input_tokens + output_tokens)

                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens

                    # Calculate cost
                    cost = None
                    if INPUT_COST_PER_M is not None and OUTPUT_COST_PER_M is not None:
                        cost = (input_tokens / 1_000_000 * INPUT_COST_PER_M) + (output_tokens / 1_000_000 * OUTPUT_COST_PER_M)
                        total_cost += cost

                    # Calculate output size
                    metadata_json = json.dumps(metadata.model_dump())
                    output_chars = len(metadata_json)

                    if print_llm_response:
                        # Print the parsed structured response (what we store) for debugging/test runs.
                        # Use ensure_ascii=True to avoid Windows console encoding issues.
                        print("\n  ---- LLM structured response (JSON) ----")
                        print(json.dumps(metadata.model_dump(), indent=2, ensure_ascii=True))
                        print("  ---- end response ----\n")

                    _safe_print("  [OK] Success")
                    _safe_print(f"    Confidence: {metadata.confidence_score:.2f}")
                    _safe_print(f"    Extracted: {len(metadata.topics)} topics, {len(metadata.keywords)} keywords, {len(metadata.project_candidates)} projects")
                    if usage:
                        _safe_print(f"    Tokens: {input_tokens:,} input + {output_tokens:,} output = {total_tokens:,} total")
                        if cost is not None:
                            _safe_print(f"    Cost: ${cost:.4f}")
                    _safe_print(f"    Output size: {output_chars:,} characters")
                    _safe_print(f"    Time: {conv_elapsed:.1f}s")
                    succeeded += 1
                else:
                    _safe_print("  [FAIL] Failed to extract metadata")
                    if result.get("error"):
                        _safe_print(f"    Error: {result['error']}")
                    _safe_print(f"    Time: {conv_elapsed:.1f}s")
                    failed += 1

                processed += 1

                # Show running totals every 10 conversations
                if processed % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / processed
                    remaining = total - processed
                    eta_seconds = remaining * avg_time
                    eta_minutes = eta_seconds / 60

                    print("\n  ---- Progress Update ----")
                    print(f"    Processed: {processed}/{total} ({processed*100//total}%)")
                    print(f"    Success: {succeeded} | Failed: {failed}")
                    print(f"    Total Tokens: {total_input_tokens + total_output_tokens:,} (in: {total_input_tokens:,}, out: {total_output_tokens:,})")
                    print(f"    Total Cost: ${total_cost:.4f}")
                    print(f"    Avg Time: {avg_time:.1f}s/conversation")
                    print(f"    ETA: {eta_minutes:.1f} minutes ({remaining} remaining)")
    
    conn.close()
    
    total_elapsed = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"Processing Complete!")
    print(f"{'='*70}")
    print(f"  Total Conversations: {total}")
    print(f"  Succeeded: {succeeded}")
    print(f"  Failed: {failed}")
    print(f"  Total Time: {total_elapsed/60:.1f} minutes ({total_elapsed:.1f} seconds)")
    print(f"  Average Time: {total_elapsed/total:.1f}s per conversation")
    print(f"\n  Token Usage:")
    print(f"    Input Tokens: {total_input_tokens:,}")
    print(f"    Output Tokens: {total_output_tokens:,}")
    print(f"    Total Tokens: {total_input_tokens + total_output_tokens:,}")
    print(f"\n  Estimated Cost:")
    if INPUT_COST_PER_M is not None and OUTPUT_COST_PER_M is not None:
        print(f"    Input: ${total_input_tokens / 1_000_000 * INPUT_COST_PER_M:.4f}")
        print(f"    Output: ${total_output_tokens / 1_000_000 * OUTPUT_COST_PER_M:.4f}")
        print(f"    Total: ${total_cost:.4f}")
    else:
        print("    Skipped (unknown model pricing)")
    print(f"{'='*70}")


if __name__ == '__main__':
    import argparse
    import sys
    from pathlib import Path

    # Add database directory to path for imports
    project_root = Path(__file__).parent
    database_dir = project_root / "database"
    if str(database_dir) not in sys.path:
        sys.path.insert(0, str(database_dir))

    # Ensure tables exist
    from create_metadata_tables import create_metadata_tables

    create_metadata_tables(DB_PATH)

    parser = argparse.ArgumentParser(description="Extract structured metadata from conversations.")
    parser.add_argument("conversation_id", nargs="?", default=None, help="Optional specific conversation_id to process")
    parser.add_argument("--force", action="store_true", help="Regenerate metadata even if it exists")
    parser.add_argument("--test", action="store_true", help="Process a single conversation (first without metadata, or first overall with --force)")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost only (OpenAI backend); no LLM calls or DB writes")
    parser.add_argument("--output-cap", type=int, default=DEFAULT_EXPECTED_OUTPUT_TOKENS, help="Estimated output tokens per seesion (for dry-run cost estimate)")
    parser.add_argument("--backend", choices=["openai", "lmstudio"], default=DEFAULT_BACKEND, help="LLM backend")
    parser.add_argument("--lmstudio-url", default=DEFAULT_LMSTUDIO_URL, help="LM Studio base URL (e.g. http://localhost:1234/v1)")
    parser.add_argument("--lmstudio-stream", action="store_true", help="Stream tokens when using LM Studio")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of conversations processed in non-test mode (e.g. 1000)")

    args = parser.parse_args()
    force = bool(args.force)
    test_mode = bool(args.test)
    dry_run = bool(args.dry_run)
    backend = str(args.backend)
    lmstudio_url = str(args.lmstudio_url)
    lmstudio_stream = bool(args.lmstudio_stream)
    output_cap = int(args.output_cap)
    limit = args.limit if args.limit is None else int(args.limit)
    
    # In test mode, process just one conversation (first one without metadata, or first overall if --force)
    if test_mode:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        if force:
            # Get first conversation
            cursor = conn.execute('''
                SELECT conversation_id, title
                FROM conversations
                ORDER BY create_time DESC
                LIMIT 1
            ''')
        else:
            # Get first conversation without metadata
            cursor = conn.execute('''
                SELECT c.conversation_id, c.title
                FROM conversations c
                LEFT JOIN conversation_metadata m ON c.conversation_id = m.conversation_id
                WHERE m.conversation_id IS NULL
                ORDER BY c.create_time DESC
                LIMIT 1
            ''')
        
        test_conv = cursor.fetchone()
        conn.close()
        
        if test_conv:
            print(f"TEST MODE: Processing conversation '{test_conv['title']}' ({test_conv['conversation_id'][:40]}...)")
            print("="*70)
            process_conversations(
                conversation_id=test_conv['conversation_id'],
                force_regenerate=force,
                limit=None,
                print_llm_response=True,
                dry_run=dry_run,
                expected_output_tokens=output_cap,
                backend=backend,
                lmstudio_url=lmstudio_url,
                lmstudio_stream=lmstudio_stream,
            )
        else:
            print("No conversations found for test mode.")
    else:
        # Normal mode - process conversations
        conv_id = args.conversation_id
        
        process_conversations(
            conversation_id=conv_id,
            force_regenerate=force,
            limit=limit,
            dry_run=dry_run,
            expected_output_tokens=output_cap,
            backend=backend,
            lmstudio_url=lmstudio_url,
            lmstudio_stream=lmstudio_stream,
        )

