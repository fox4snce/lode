"""
LM Studio OpenAI-compatible client (local).

Targets the OpenAI-style endpoint exposed by LM Studio:
  http://127.0.0.1:1234/v1/chat/completions

No OpenAI key required. Uses only stdlib (urllib) so it works in your venv
without adding dependencies.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def chat_completions(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    base_url: str = "http://127.0.0.1:1234/v1",
    temperature: float = 0.7,
    max_tokens: int = -1,
    stream: bool = True,
    print_stream: bool = True,
    timeout_s: int = 600,
) -> str:
    """
    Call LM Studio's OpenAI-compatible /v1/chat/completions endpoint.

    Returns the full assistant text (accumulated). If stream=True and print_stream=True,
    prints tokens as they arrive (similar to curl stream).
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload: Dict[str, Any] = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    # If model is omitted, LM Studio will use the currently loaded model.
    if model:
        payload["model"] = model

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=timeout_s)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"LM Studio HTTP {e.code}: {e.reason}. Body: {body}") from e

    with resp:
        if not stream:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""

        # Streaming mode (OpenAI-compatible SSE: "data: {...}" lines, terminated by "data: [DONE]")
        full = []
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if not line.startswith("data:"):
                continue
            chunk = line[len("data:") :].strip()
            if chunk == "[DONE]":
                break
            try:
                event = json.loads(chunk)
            except json.JSONDecodeError:
                continue

            # OpenAI streaming shape: choices[0].delta.content
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            text = delta.get("content")
            if not text:
                continue
            full.append(text)
            if print_stream:
                try:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                except UnicodeEncodeError:
                    # Fallback for Windows console encoding issues
                    try:
                        sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
                        sys.stdout.flush()
                    except Exception:
                        pass  # Skip printing if still fails

        if print_stream:
            try:
                sys.stdout.write("\n")
                sys.stdout.flush()
            except UnicodeEncodeError:
                try:
                    sys.stdout.buffer.write(b"\n")
                    sys.stdout.flush()
                except Exception:
                    pass

        return "".join(full)


def extract_json_object(text: str) -> str:
    """
    Best-effort extraction of a single JSON object from model output.
    Removes common wrappers like ```json fences, and trims to outermost {...}.
    """
    s = text.strip()
    if s.startswith("```"):
        # strip first fence line
        lines = s.splitlines()
        if len(lines) >= 2:
            s = "\n".join(lines[1:])
        # strip ending fence
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3].rstrip()

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return s
    return s[start : end + 1]


def unwrap_common_wrapper(data: Any) -> Any:
    """
    Some local models wrap outputs like {"response": {...}} or {"result": {...}}.
    If we detect a single-key wrapper around a dict, unwrap it.
    """
    if isinstance(data, dict) and len(data) == 1:
        (k, v), = data.items()
        if k in ("response", "result", "data", "output") and isinstance(v, dict):
            return v
    return data


