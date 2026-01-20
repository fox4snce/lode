"""
Tests for feature flag system (core vs pro builds).
"""

import unittest
import os
from unittest.mock import patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestFeatureFlags(unittest.TestCase):
    """Test feature flag system."""
    
    def setUp(self):
        """Clear any cached values."""
        # Import here to avoid module-level caching issues
        if 'backend.feature_flags' in sys.modules:
            del sys.modules['backend.feature_flags']
    
    def test_core_build_default(self):
        """Test that default build type is core."""
        with patch.dict(os.environ, {}, clear=True):
            from backend.feature_flags import is_pro_build, is_feature_enabled
            
            self.assertFalse(is_pro_build())
            self.assertFalse(is_feature_enabled("vectordb"))
            self.assertFalse(is_feature_enabled("chat"))
            self.assertTrue(is_feature_enabled("import"))  # Core feature
    
    def test_pro_build_flag(self):
        """Test that pro build flag works."""
        with patch.dict(os.environ, {"LODE_BUILD_TYPE": "pro"}, clear=False):
            from backend.feature_flags import is_pro_build, is_feature_enabled
            
            self.assertTrue(is_pro_build())
            self.assertTrue(is_feature_enabled("vectordb"))
            self.assertTrue(is_feature_enabled("chat"))
            self.assertTrue(is_feature_enabled("import"))  # Core feature
    
    def test_core_build_explicit(self):
        """Test explicit core build flag."""
        with patch.dict(os.environ, {"LODE_BUILD_TYPE": "core"}, clear=False):
            from backend.feature_flags import is_pro_build, is_feature_enabled
            
            self.assertFalse(is_pro_build())
            self.assertFalse(is_feature_enabled("vectordb"))
            self.assertFalse(is_feature_enabled("chat"))
    
    def test_unknown_feature(self):
        """Test that unknown features default to enabled (backwards compatible)."""
        with patch.dict(os.environ, {}, clear=True):
            from backend.feature_flags import is_feature_enabled
            
            # Unknown features should be enabled by default (backwards compat)
            self.assertTrue(is_feature_enabled("unknown_feature"))


if __name__ == "__main__":
    unittest.main()
