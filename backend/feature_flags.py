"""
Feature flag system for core vs pro builds.

Features can be gated based on build type:
- Core: Basic features (import, search, analytics, export)
- Pro: All core features + VectorDB + Chat
"""

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def is_pro_build() -> bool:
    """
    Check if this is a pro build.
    
    Determined by LODE_BUILD_TYPE environment variable:
    - "pro" -> True
    - "core" or unset -> False
    """
    build_type = os.getenv("LODE_BUILD_TYPE", "core").lower()
    return build_type == "pro"


@lru_cache(maxsize=32)
def is_feature_enabled(feature: str) -> bool:
    """
    Check if a feature is enabled.
    
    Args:
        feature: Feature name (e.g., "vectordb", "chat", "import")
    
    Returns:
        True if feature is enabled, False otherwise
    """
    # Pro-only features
    pro_features = {"vectordb", "chat"}
    
    if feature in pro_features:
        return is_pro_build()
    
    # Core features and unknown features are enabled by default
    # (backwards compatibility: unknown features don't break)
    return True


def get_build_type() -> str:
    """Get current build type as string."""
    return "pro" if is_pro_build() else "core"
