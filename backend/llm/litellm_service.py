"""
LiteLLM service for unified LLM access.

Provides:
- Provider/model detection based on API keys
- Unified LLM calling interface
"""

import os
from typing import List, Dict, Any, Optional
from typing import Iterator

_LITELLM_IMPORT_ERROR: Optional[str] = None

try:
    from litellm import completion
    import litellm
    # Drop unsupported params to avoid errors with models like gpt-5
    litellm.drop_params = True
    LITELLM_AVAILABLE = True
except ImportError as e:
    _LITELLM_IMPORT_ERROR = f"ImportError: {e}"
    LITELLM_AVAILABLE = False
    completion = None
    litellm = None
except Exception as e:
    # In frozen builds, imports can fail for non-ImportError reasons (missing optional deps/data).
    # Capture the real error so the UI can surface it (without leaking keys).
    _LITELLM_IMPORT_ERROR = f"{type(e).__name__}: {e}"
    LITELLM_AVAILABLE = False
    completion = None
    litellm = None


def _ensure_litellm() -> None:
    if LITELLM_AVAILABLE:
        return
    openai_present = bool(os.getenv("OPENAI_API_KEY"))
    anthropic_present = bool(os.getenv("ANTHROPIC_API_KEY"))
    extra = f" (import error: {_LITELLM_IMPORT_ERROR})" if _LITELLM_IMPORT_ERROR else ""
    raise Exception(
        "LiteLLM is unavailable in this runtime"
        f"{extra}. "
        f"Env keys present: OPENAI_API_KEY={openai_present}, ANTHROPIC_API_KEY={anthropic_present}"
    )


def _normalize_kwargs_for_model(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize provider/model-specific kwargs so "Test Model" and "Chat" behave consistently.

    In particular, some OpenAI gpt-5* models reject `temperature` and/or `max_tokens`
    (preferring `max_completion_tokens`).
    """
    model = str(kwargs.get("model") or "")
    if model.startswith("openai/"):
        name = model.split("/", 1)[1] if "/" in model else model
        if name.startswith("gpt-5"):
            # Be conservative: align with the minimal param set used by "Test Model".
            if "max_tokens" in kwargs and "max_completion_tokens" not in kwargs:
                kwargs = dict(kwargs)
                kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
            if "temperature" in kwargs:
                kwargs = dict(kwargs)
                kwargs.pop("temperature", None)
    return kwargs


def get_available_providers() -> List[Dict[str, Any]]:
    """
    Get list of available providers.
    
    Returns:
        List of provider dicts with keys:
        - provider: str (e.g., "openai", "anthropic")
        - name: str (display name)
        - placeholder: str (example model name for this provider)
    """
    # Chat tab: OpenAI and Anthropic only for now; others in a future version.
    providers = [
        {
            "provider": "openai",
            "name": "OpenAI",
            "placeholder": "gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo"
        },
        {
            "provider": "anthropic",
            "name": "Anthropic",
            "placeholder": "claude-sonnet-4-20250514, claude-3-5-sonnet-20241022"
        },
    ]
    return providers


def format_model_name(provider: str, model: str) -> str:
    """
    Format model name for LiteLLM based on provider.
    
    Args:
        provider: Provider name (openai, anthropic, lmstudio, ollama, custom)
        model: Model name/identifier
    
    Returns:
        Formatted model string for LiteLLM
    """
    model = model.strip()
    
    if provider == "custom":
        # Custom provider - assume user knows the format (e.g., "openai/gpt-4o")
        return model
    
    if provider == "lmstudio":
        # LM Studio uses openai-compatible API
        # LiteLLM supports: openai/<model> with base_url set to LM Studio
        # For now, format as openai/... and user needs to set LITELLM_API_BASE
        return f"openai/{model}"
    
    if provider == "ollama":
        # Ollama format
        return f"ollama/{model}"
    
    # OpenAI, Anthropic, etc. - prefix with provider
    return f"{provider}/{model}"


def call_llm(
    messages: List[Dict[str, str]],
    model: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Call LLM via LiteLLM.
    
    Args:
        messages: List of message dicts with "role" and "content"
        model: Model identifier (e.g., "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514")
        temperature: Optional sampling temperature (0.0-2.0). If None, uses model default.
        max_tokens: Optional maximum tokens to generate
    
    Returns:
        Generated text response
    
    Raises:
        Exception: If LLM call fails or LiteLLM is not available
    """
    _ensure_litellm()
    
    # Keep this wrapper *thin* and LiteLLM-first:
    # - Call litellm.completion() with standard params
    # - If the provider/model rejects a known param, retry once with the minimal fix
    def _do_call(kwargs: Dict[str, Any]) -> str:
        resp = completion(**kwargs)
        # Be defensive: some models/providers can return empty content (e.g. reasoning-only)
        try:
            return resp.choices[0].message.content or ""
        except Exception:
            return ""

    # Build kwargs - only include params that are provided
    kwargs: Dict[str, Any] = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    kwargs = _normalize_kwargs_for_model(kwargs)

    try:
        return _do_call(kwargs)
    except Exception as e:
        msg = str(e)

        # Known OpenAI gpt-5 style param mismatch:
        # "Unsupported parameter: 'max_tokens' ... Use 'max_completion_tokens' instead."
        if "max_tokens" in kwargs and "max_completion_tokens" in msg and "not supported" in msg:
            retry_kwargs = dict(kwargs)
            retry_kwargs["max_completion_tokens"] = retry_kwargs.pop("max_tokens")
            try:
                return _do_call(retry_kwargs)
            except Exception as e2:
                raise Exception(f"LLM call failed: {e2}")

        # Known temperature incompatibility (e.g. some gpt-5 variants):
        if "temperature" in kwargs and ("don't support temperature" in msg or "UnsupportedParamsError" in msg):
            retry_kwargs = dict(kwargs)
            retry_kwargs.pop("temperature", None)
            try:
                return _do_call(retry_kwargs)
            except Exception as e2:
                raise Exception(f"LLM call failed: {e2}")

        raise Exception(f"LLM call failed: {e}")


def call_llm_stream(
    messages: List[Dict[str, str]],
    model: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Iterator[str]:
    """
    Streaming LLM call via LiteLLM. Yields text deltas.
    """
    _ensure_litellm()

    def _extract_delta(chunk: Any) -> str:
        # LiteLLM aims for OpenAI-compatible streaming chunks, but be defensive.
        try:
            choice = chunk.choices[0]
            # OpenAI-style object
            delta = getattr(choice, "delta", None)
            if delta is not None:
                return getattr(delta, "content", "") or ""
            msg = getattr(choice, "message", None)
            if msg is not None:
                return getattr(msg, "content", "") or ""
        except Exception:
            pass
        # Dict-like fallback
        try:
            choices = chunk.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                return delta.get("content") or ""
        except Exception:
            pass
        return ""

    kwargs: Dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    kwargs = _normalize_kwargs_for_model(kwargs)

    try:
        stream = completion(**kwargs)
    except Exception as e:
        msg = str(e)
        if "max_tokens" in kwargs and "max_completion_tokens" in msg and "not supported" in msg:
            retry = dict(kwargs)
            retry["max_completion_tokens"] = retry.pop("max_tokens")
            stream = completion(**retry)
        elif "temperature" in kwargs and ("don't support temperature" in msg or "UnsupportedParamsError" in msg):
            retry = dict(kwargs)
            retry.pop("temperature", None)
            stream = completion(**retry)
        else:
            raise Exception(f"LLM call failed: {e}")

    for chunk in stream:
        delta = _extract_delta(chunk)
        if delta:
            yield delta
