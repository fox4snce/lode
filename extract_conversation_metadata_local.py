"""
Local (LM Studio) metadata extraction pipeline: split into small requests.

Design goals:
- Do as much as possible with normal programming (counts, timestamps, etc.)
- For LLM-derived fields, make single-purpose calls (topics, keywords, title, summary, etc.)
- No Structured Outputs (local models often won't follow strict schemas)
- Re-runnable: by default only fills missing fields; use --force to overwrite

LM Studio endpoint:
  http://127.0.0.1:1234/v1/chat/completions

Example:
  python extract_conversation_metadata_local.py --test
  python extract_conversation_metadata_local.py --test --force
  python extract_conversation_metadata_local.py --force
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from lmstudio_llm import chat_completions, extract_json_object, unwrap_common_wrapper


DB_PATH = "conversations.db"
DEFAULT_LMSTUDIO_URL = "http://127.0.0.1:1234/v1"

# Keep requests fast by default; increase if you want more context.
DEFAULT_MAX_CHARS = 30_000

JSON_ONLY_SYSTEM = (
    "You are a JSON generator. Output MUST be valid JSON and NOTHING else. "
    "No markdown, no code fences, no commentary, no extra keys."
)


def _utc_iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.utcfromtimestamp(float(ts)).isoformat() + "Z"
    except Exception:
        return None


def get_conversation_row(conn: sqlite3.Connection, conversation_id: str) -> Optional[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT conversation_id, title, create_time, update_time, ai_source
        FROM conversations
        WHERE conversation_id = ?
        """,
        (conversation_id,),
    )
    return cur.fetchone()


def get_conversation_messages(conn: sqlite3.Connection, conversation_id: str) -> List[Dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT m.message_id, m.role, m.content, m.create_time
        FROM messages m
        WHERE m.conversation_id = ?
        ORDER BY m.create_time ASC, m.id ASC
        """,
        (conversation_id,),
    )
    out: List[Dict[str, Any]] = []
    for row in cur.fetchall():
        out.append(
            {
                "message_id": row[0],
                "role": row[1],
                "content": row[2] or "",
                "create_time": row[3],
            }
        )
    return out


def format_conversation_for_llm(messages: List[Dict[str, Any]], max_chars: Optional[int]) -> str:
    formatted: List[str] = []
    total = 0
    for m in messages:
        line = f"[{m['role']}] ({m['message_id']}): {m['content']}\n"
        if max_chars is not None and total + len(line) > max_chars:
            formatted.append(f"\n[TRUNCATED - {len(messages)} total messages]\n")
            break
        formatted.append(line)
        total += len(line)
    return "".join(formatted)


def compute_programmatic_metadata(conv_row: sqlite3.Row, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    roles = [m["role"] for m in messages]
    role_counts: Dict[str, int] = {}
    for r in roles:
        role_counts[r] = role_counts.get(r, 0) + 1

    total_chars = sum(len(m.get("content", "") or "") for m in messages)
    total_lines = sum((m.get("content", "") or "").count("\n") + 1 for m in messages if (m.get("content") or "").strip())

    first_ts = messages[0]["create_time"] if messages else None
    last_ts = messages[-1]["create_time"] if messages else None

    return {
        "conversation_id": conv_row["conversation_id"],
        "ai_source": conv_row["ai_source"],
        "db_title": conv_row["title"],
        "create_time": conv_row["create_time"],
        "update_time": conv_row["update_time"],
        "create_time_iso": _utc_iso(conv_row["create_time"]),
        "update_time_iso": _utc_iso(conv_row["update_time"]),
        "first_message_time": first_ts,
        "last_message_time": last_ts,
        "first_message_time_iso": _utc_iso(first_ts),
        "last_message_time_iso": _utc_iso(last_ts),
        "num_messages": len(messages),
        "role_counts": role_counts,
        "total_chars": total_chars,
        "approx_lines": total_lines,
    }


def load_existing_metadata(conn: sqlite3.Connection, conversation_id: str) -> Optional[Dict[str, Any]]:
    cur = conn.execute(
        "SELECT metadata_json FROM conversation_metadata WHERE conversation_id = ?",
        (conversation_id,),
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def store_metadata_json(
    conn: sqlite3.Connection,
    conversation_id: str,
    metadata: Dict[str, Any],
    schema_version: str,
    model_used: str,
    confidence_score: Optional[float],
) -> None:
    cur = conn.cursor()
    metadata_json = json.dumps(metadata, ensure_ascii=True)
    cur.execute(
        """
        INSERT OR REPLACE INTO conversation_metadata
        (conversation_id, metadata_json, schema_version, model_used, confidence_score, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (conversation_id, metadata_json, schema_version, model_used, confidence_score),
    )

    # indexed fields (keep minimal; only what we actually use)
    cur.execute("DELETE FROM conversation_metadata_indexed WHERE conversation_id = ?", (conversation_id,))
    for t in metadata.get("topics", []) or []:
        cur.execute(
            """
            INSERT OR IGNORE INTO conversation_metadata_indexed (conversation_id, field_type, field_name, field_value)
            VALUES (?, 'topic', 'topic', ?)
            """,
            (conversation_id, str(t)),
        )
    for k in metadata.get("keywords", []) or []:
        cur.execute(
            """
            INSERT OR IGNORE INTO conversation_metadata_indexed (conversation_id, field_type, field_name, field_value)
            VALUES (?, 'keyword', 'keyword', ?)
            """,
            (conversation_id, str(k)),
        )
    if metadata.get("status"):
        cur.execute(
            """
            INSERT OR IGNORE INTO conversation_metadata_indexed (conversation_id, field_type, field_name, field_value)
            VALUES (?, 'status', 'status', ?)
            """,
            (conversation_id, str(metadata["status"])),
        )
    conn.commit()


def _parse_json_list(text: str) -> List[str]:
    s = extract_json_object(text)
    try:
        data = json.loads(s)
        data = unwrap_common_wrapper(data)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    out: List[str] = []
    for x in data:
        sx = str(x).strip()
        if sx:
            out.append(sx)
    return out


def _parse_json_string(text: str) -> str:
    s = text.strip()
    try:
        obj = json.loads(extract_json_object(s))
        obj = unwrap_common_wrapper(obj)
        if isinstance(obj, str):
            return obj.strip()
        if isinstance(obj, dict) and len(obj) == 1:
            return str(list(obj.values())[0]).strip()
    except Exception:
        return ""
    return ""


def _lm_call(
    *,
    base_url: str,
    stream: bool,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int = -1,
    debug: bool = False,
) -> str:
    text = chat_completions(
        base_url=base_url,
        model=None,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        print_stream=stream,
    )
    if debug:
        print("\n--- RAW LLM OUTPUT ---")
        print(text)
        print("--- END RAW ---\n")
    return text


def _lm_json_list(
    *,
    base_url: str,
    stream: bool,
    user: str,
    temperature: float = 0.2,
    max_items: int,
    debug: bool = False,
) -> List[str]:
    # Attempt 1
    text = _lm_call(base_url=base_url, stream=stream, system=JSON_ONLY_SYSTEM, user=user, temperature=temperature, debug=debug)
    items = _parse_json_list(text)
    if items:
        return items[:max_items]

    # Attempt 2: stronger, include explicit example and "return [] on failure"
    repair_user = (
        user
        + "\n\nIf you cannot comply exactly, return [] (empty JSON array).\n"
        + f"Example: [\"item1\", \"item2\"]\n"
    )
    text2 = _lm_call(base_url=base_url, stream=stream, system=JSON_ONLY_SYSTEM, user=repair_user, temperature=0.0, debug=debug)
    items2 = _parse_json_list(text2)
    return items2[:max_items]


def _lm_json_string(
    *,
    base_url: str,
    stream: bool,
    user: str,
    temperature: float = 0.2,
    max_chars: int,
    debug: bool = False,
) -> str:
    text = _lm_call(base_url=base_url, stream=stream, system=JSON_ONLY_SYSTEM, user=user, temperature=temperature, debug=debug)
    s = _parse_json_string(text)
    if s:
        return s[:max_chars]

    repair_user = (
        user
        + "\n\nIf you cannot comply exactly, return \"\" (empty JSON string).\n"
        + "Example: \"My title\"\n"
    )
    text2 = _lm_call(base_url=base_url, stream=stream, system=JSON_ONLY_SYSTEM, user=repair_user, temperature=0.0, debug=debug)
    s2 = _parse_json_string(text2)
    return (s2 or "")[:max_chars]


def llm_topics(conversation_text: str, base_url: str, stream: bool, debug: bool = False) -> List[str]:
    user = (
        "Return a JSON array of up to 8 short topic strings.\n"
        "Do NOT include quotes from the conversation.\n\n"
        "Conversation:\n"
        f"{conversation_text}"
    )
    return _lm_json_list(base_url=base_url, stream=stream, user=user, max_items=8, debug=debug)


def llm_keywords(conversation_text: str, base_url: str, stream: bool, debug: bool = False) -> List[str]:
    user = (
        "Return a JSON array of up to 12 keywords.\n"
        "Do NOT include full sentences.\n\n"
        "Conversation:\n"
        f"{conversation_text}"
    )
    return _lm_json_list(base_url=base_url, stream=stream, user=user, max_items=12, debug=debug)


def llm_title(conversation_text: str, base_url: str, stream: bool, debug: bool = False) -> str:
    user = (
        "Return a JSON string that is a short title (<= 120 chars).\n\n"
        "Conversation:\n"
        f"{conversation_text}"
    )
    return _lm_json_string(base_url=base_url, stream=stream, user=user, max_chars=120, debug=debug)


def llm_summary(conversation_text: str, base_url: str, stream: bool, debug: bool = False) -> str:
    user = (
        "Return a JSON string that is a one-paragraph summary (<= 500 chars).\n\n"
        "Conversation:\n"
        f"{conversation_text}"
    )
    return _lm_json_string(base_url=base_url, stream=stream, user=user, max_chars=500, debug=debug)


def llm_types(conversation_text: str, base_url: str, stream: bool, debug: bool = False) -> List[str]:
    user = (
        "Return a JSON array of up to 5 short conversation type tags.\n"
        "Example: [\"analysis\", \"writing\"].\n\n"
        "Conversation:\n"
        f"{conversation_text}"
    )
    return _lm_json_list(base_url=base_url, stream=stream, user=user, max_items=5, debug=debug)


def llm_intents(conversation_text: str, base_url: str, stream: bool, debug: bool = False) -> List[str]:
    user = (
        "Return a JSON array of up to 5 short intent tags.\n"
        "Example: [\"analyze\", \"explore\"].\n\n"
        "Conversation:\n"
        f"{conversation_text}"
    )
    return _lm_json_list(base_url=base_url, stream=stream, user=user, max_items=5, debug=debug)


def llm_status(conversation_text: str, base_url: str, stream: bool, debug: bool = False) -> str:
    user = (
        "Return a JSON string that is exactly one of: \"resolved\", \"ongoing\", \"abandoned\", \"unclear\".\n\n"
        "Conversation:\n"
        f"{conversation_text}"
    )
    out = _lm_json_string(base_url=base_url, stream=stream, user=user, max_chars=32, temperature=0.0, debug=debug)
    s = (out or "").lower().strip()
    if s not in ("resolved", "ongoing", "abandoned", "unclear"):
        s = "unclear"
    return s


def select_conversations(conn: sqlite3.Connection, force: bool) -> List[sqlite3.Row]:
    if force:
        cur = conn.execute("SELECT conversation_id, title FROM conversations ORDER BY create_time DESC")
        return cur.fetchall()
    cur = conn.execute(
        """
        SELECT c.conversation_id, c.title
        FROM conversations c
        LEFT JOIN conversation_metadata m ON c.conversation_id = m.conversation_id
        WHERE m.conversation_id IS NULL
        ORDER BY c.create_time DESC
        """
    )
    return cur.fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--url", default=DEFAULT_LMSTUDIO_URL)
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    ap.add_argument("--stream", action="store_true", help="Stream tokens in console for each LLM call")
    ap.add_argument("--debug-raw", action="store_true", help="Print raw LLM outputs for each step (test/dev)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing metadata (otherwise fill missing only)")
    ap.add_argument("--test", action="store_true", help="Run only one conversation")
    ap.add_argument("--conversation-id", default=None)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # Ensure tables exist (re-use existing helper)
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent
    database_dir = project_root / "database"
    if str(database_dir) not in sys.path:
        sys.path.insert(0, str(database_dir))
    from create_metadata_tables import create_metadata_tables

    create_metadata_tables(args.db)

    if args.conversation_id:
        convs = [sqlite3.Row]  # type: ignore
        cur = conn.execute(
            "SELECT conversation_id, title FROM conversations WHERE conversation_id = ?",
            (args.conversation_id,),
        )
        row = cur.fetchone()
        convs = [row] if row else []
    else:
        convs = select_conversations(conn, force=args.force)

    if args.test and len(convs) > 1:
        convs = convs[:1]

    if not convs:
        print("No conversations selected.")
        conn.close()
        return 0

    print(f"Selected {len(convs)} conversation(s). Backend: LM Studio @ {args.url}")

    schema_version = "local_split_v1"
    model_used = "lmstudio"

    for idx, conv in enumerate(convs, start=1):
        conv_id = conv["conversation_id"]
        title = conv["title"] or "Untitled"
        print(f"\n[{idx}/{len(convs)}] {title} ({conv_id[:24]}...)")

        conv_row = get_conversation_row(conn, conv_id)
        if not conv_row:
            print("  Skipped: conversation row not found")
            continue

        messages = get_conversation_messages(conn, conv_id)
        convo_text = format_conversation_for_llm(messages, max_chars=args.max_chars if args.max_chars > 0 else None)

        existing = load_existing_metadata(conn, conv_id) or {}
        meta: Dict[str, Any] = dict(existing)

        # Always compute/free fields
        meta["_stats"] = compute_programmatic_metadata(conv_row, messages)

        # LLM fields: only fill missing unless --force
        def need(key: str) -> bool:
            return args.force or key not in meta or meta.get(key) in (None, "", [], {})

        t0 = time.time()
        if need("topics"):
            meta["topics"] = llm_topics(convo_text, base_url=args.url, stream=args.stream, debug=args.debug_raw)
        if need("keywords"):
            meta["keywords"] = llm_keywords(convo_text, base_url=args.url, stream=args.stream, debug=args.debug_raw)
        if need("title"):
            meta["title"] = llm_title(convo_text, base_url=args.url, stream=args.stream, debug=args.debug_raw)
        if need("summary"):
            meta["summary"] = llm_summary(convo_text, base_url=args.url, stream=args.stream, debug=args.debug_raw)
        if need("conversation_types"):
            meta["conversation_types"] = llm_types(convo_text, base_url=args.url, stream=args.stream, debug=args.debug_raw)
        if need("intents"):
            meta["intents"] = llm_intents(convo_text, base_url=args.url, stream=args.stream, debug=args.debug_raw)
        if need("status"):
            meta["status"] = llm_status(convo_text, base_url=args.url, stream=args.stream, debug=args.debug_raw)

        # light metadata about metadata
        meta["schema_version"] = schema_version
        meta["model_used"] = model_used
        meta["extracted_at"] = datetime.utcnow().isoformat() + "Z"

        # store (local mode: no confidence)
        store_metadata_json(conn, conv_id, meta, schema_version=schema_version, model_used=model_used, confidence_score=None)
        print(f"  Stored. Elapsed: {time.time() - t0:.1f}s")

        if args.test:
            print("\n--- METADATA JSON (stored) ---")
            print(json.dumps(meta, indent=2, ensure_ascii=True))

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


