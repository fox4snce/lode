"""
Tests for LiteLLM service integration.
"""

import unittest
import os
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestLiteLLMService(unittest.TestCase):
    """Test LiteLLM service."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear any cached modules
        modules_to_clear = [
            'backend.llm.litellm_service',
            'litellm',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
    
    def test_get_available_providers_openai(self):
        """Test provider detection with OpenAI key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            from backend.llm.litellm_service import get_available_providers
            
            providers = get_available_providers()
            
            # Should find OpenAI
            openai_providers = [p for p in providers if p["provider"] == "openai"]
            self.assertGreater(len(openai_providers), 0)

            # New contract: provider has a placeholder (user types the model)
            if openai_providers:
                self.assertIn("placeholder", openai_providers[0])
                self.assertTrue(isinstance(openai_providers[0]["placeholder"], str))
                self.assertGreater(len(openai_providers[0]["placeholder"]), 0)
    
    def test_get_available_providers_anthropic(self):
        """Test provider detection with Anthropic key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            from backend.llm.litellm_service import get_available_providers
            
            providers = get_available_providers()
            
            # Should find Anthropic
            anthropic_providers = [p for p in providers if p["provider"] == "anthropic"]
            self.assertGreater(len(anthropic_providers), 0)
    
    def test_get_available_providers_no_keys(self):
        """Test provider detection with no API keys."""
        with patch.dict(os.environ, {}, clear=True):
            from backend.llm.litellm_service import get_available_providers
            
            providers = get_available_providers()
            
            # Should return empty list or minimal providers
            # (Implementation may return empty list or providers that don't need keys)
            self.assertIsInstance(providers, list)
    
    def test_call_llm_success(self):
        """Test successful LLM call."""
        # Mock litellm.completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        
        with patch('litellm.completion', return_value=mock_response):
            from backend.llm.litellm_service import call_llm
            
            messages = [{"role": "user", "content": "Hello"}]
            result = call_llm(messages, "openai/gpt-4o")
            
            self.assertEqual(result, "Test response")
    
    def test_call_llm_failure(self):
        """Test LLM call failure handling."""
        with patch('litellm.completion', side_effect=Exception("API Error")):
            from backend.llm.litellm_service import call_llm
            
            messages = [{"role": "user", "content": "Hello"}]
            
            with self.assertRaises(Exception) as context:
                call_llm(messages, "openai/gpt-4o")
            
            self.assertIn("LLM call failed", str(context.exception))


if __name__ == "__main__":
    unittest.main()
