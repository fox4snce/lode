"""
LiteLLM service for unified LLM access.

Provides:
- Provider/model detection based on API keys
- Unified LLM calling interface
"""

import os
from typing import List, Dict, Any, Optional

try:
    from litellm import completion
    import litellm
    # Drop unsupported params to avoid errors with models like gpt-5
    litellm.drop_params = True
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    completion = None
    litellm = None


def get_available_providers() -> List[Dict[str, Any]]:
    """
    Get list of available providers.
    
    Returns:
        List of provider dicts with keys:
        - provider: str (e.g., "openai", "anthropic")
        - name: str (display name)
        - placeholder: str (example model name for this provider)
    """
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
        {
            "provider": "lmstudio",
            "name": "LM Studio",
            "placeholder": "local model name (e.g., llama-3, mistral)"
        },
        {
            "provider": "ollama",
            "name": "Ollama",
            "placeholder": "local model name (e.g., llama3, mistral)"
        },
        {
            "provider": "custom",
            "name": "Custom",
            "placeholder": "provider/model (e.g., openai/gpt-4o, anthropic/claude-3)"
        }
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
    if not LITELLM_AVAILABLE:
        raise Exception("LiteLLM is not installed. Install with: pip install litellm")
    
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
