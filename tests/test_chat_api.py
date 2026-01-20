"""
Integration tests for chat API endpoints.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestChatAPI(unittest.TestCase):
    """Test chat API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client with chat routes enabled."""
        # Set environment to enable pro features
        os.environ["LODE_BUILD_TYPE"] = "pro"
        
        # Clear caches
        import backend.feature_flags
        backend.feature_flags.is_pro_build.cache_clear()
        backend.feature_flags.is_feature_enabled.cache_clear()
        
        # Import app (routes will be registered if feature is enabled)
        from backend.main import app
        cls.app = app
        from fastapi.testclient import TestClient
        cls.client = TestClient(app)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up environment."""
        if "LODE_BUILD_TYPE" in os.environ:
            del os.environ["LODE_BUILD_TYPE"]
        import backend.feature_flags
        backend.feature_flags.is_pro_build.cache_clear()
        backend.feature_flags.is_feature_enabled.cache_clear()
    
    @patch('backend.routes.chat.call_llm')
    @patch('backend.routes.chat.search_phrases')
    @patch('backend.routes.chat.improve_query_for_search')
    def test_chat_completion_success(self, mock_improve, mock_search_phrases, mock_llm):
        """Test successful chat completion."""
        # Mock query improvement
        mock_improve.return_value = "improved query"
        
        # Mock vector search (search_phrases is called by search_vectordb)
        mock_search_phrases.return_value = [
            {
                "phrase": "improved query",
                "results": [
                    {
                        "similarity": 0.8,
                        "content": "Test context",
                        "metadata": {"title": "Test"}
                    }
                ]
            }
        ]
        
        # Mock LLM response
        mock_llm.return_value = "This is a test response"
        
        response = self.client.post(
            "/api/chat/completion",
            json={
                "query": "What is spacetime?",
                "model": "openai/gpt-4o",
                "history": [],
                "context_window_size": 4000,
                "min_similarity": 0.5,
                "max_context_chunks": 5
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("response", data)
        self.assertIn("improved_query", data)
        self.assertEqual(data["response"], "This is a test response")
    
    def test_chat_completion_feature_disabled(self):
        """Test chat completion when feature is disabled."""
        # Temporarily disable feature
        import backend.feature_flags
        original_env = os.environ.get("LODE_BUILD_TYPE")
        if "LODE_BUILD_TYPE" in os.environ:
            del os.environ["LODE_BUILD_TYPE"]
        backend.feature_flags.is_pro_build.cache_clear()
        backend.feature_flags.is_feature_enabled.cache_clear()
        
        try:
            # Router won't be registered, so we'll get 404
            # Or if router is registered but endpoint checks flag, we'll get 403
            response = self.client.post(
                "/api/chat/completion",
                json={
                    "query": "Test",
                    "model": "openai/gpt-4o"
                }
            )
            
            # Should return 403 or 404 depending on implementation
            self.assertIn(response.status_code, [403, 404])
        finally:
            # Restore
            if original_env:
                os.environ["LODE_BUILD_TYPE"] = original_env
            backend.feature_flags.is_pro_build.cache_clear()
            backend.feature_flags.is_feature_enabled.cache_clear()
    
    @patch('backend.llm.litellm_service.get_available_providers')
    def test_get_providers(self, mock_get_providers):
        """Test getting available providers."""
        mock_get_providers.return_value = [
            {
                "provider": "openai",
                "models": ["gpt-4o", "gpt-4o-mini"],
                "name": "OpenAI"
            }
        ]
        
        response = self.client.get("/api/chat/providers")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("providers", data)
        self.assertGreater(len(data["providers"]), 0)


if __name__ == "__main__":
    unittest.main()
