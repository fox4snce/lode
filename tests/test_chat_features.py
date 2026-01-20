"""
Tests for chat feature components (query improvement, context filtering, history).
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestQueryImprovement(unittest.TestCase):
    """Test query improvement functionality."""
    
    def setUp(self):
        """Set up test environment."""
        if 'backend.chat.query_improver' in sys.modules:
            del sys.modules['backend.chat.query_improver']
    
    def test_improve_query_basic(self):
        """Test basic query improvement."""
        with patch('backend.chat.query_improver.call_llm', return_value="spacetime simulation"):
            from backend.chat.query_improver import improve_query_for_search
            
            result = improve_query_for_search(
                "Can you tell me about spacetime as a simulation?",
                "openai/gpt-4o"
            )
            
            self.assertEqual(result, "spacetime simulation")
    
    def test_improve_query_with_history(self):
        """Test query improvement with conversation history."""
        with patch('backend.chat.query_improver.call_llm', return_value="quantum mechanics"):
            from backend.chat.query_improver import improve_query_for_search
            
            history = [
                {"role": "user", "content": "What is physics?"},
                {"role": "assistant", "content": "Physics is..."}
            ]
            
            result = improve_query_for_search(
                "Tell me more about that quantum stuff",
                "openai/gpt-4o",
                history
            )
            
            self.assertEqual(result, "quantum mechanics")
    
    def test_improve_query_fallback(self):
        """Test that query improvement falls back to original on error."""
        with patch('backend.chat.query_improver.call_llm', return_value=""):
            from backend.chat.query_improver import improve_query_for_search
            
            original = "What is spacetime?"
            result = improve_query_for_search(original, "openai/gpt-4o")
            
            self.assertEqual(result, original)


class TestContextFiltering(unittest.TestCase):
    """Test context filtering and formatting."""
    
    def test_filter_results_by_quality(self):
        """Test filtering results by similarity score."""
        from backend.chat.context_manager import filter_results_by_quality
        
        results = [
            {"similarity": 0.8, "content": "High quality"},
            {"similarity": 0.6, "content": "Medium quality"},
            {"similarity": 0.4, "content": "Low quality"},
            {"similarity": 0.7, "content": "Good quality"},
        ]
        
        filtered = filter_results_by_quality(results, min_similarity=0.5, max_results=3)
        
        self.assertEqual(len(filtered), 3)
        self.assertGreaterEqual(filtered[0]["similarity"], 0.5)
        # Should be sorted by similarity (descending)
        self.assertGreaterEqual(filtered[0]["similarity"], filtered[-1]["similarity"])
    
    def test_format_context_for_llm(self):
        """Test context formatting for LLM."""
        from backend.chat.context_manager import format_context_for_llm
        
        results = [
            {
                "similarity": 0.8,
                "content": "This is context about spacetime.",
                "metadata": {"title": "Physics Discussion", "chunk_index": 1}
            }
        ]
        
        context = format_context_for_llm(results)
        
        self.assertIn("spacetime", context)
        self.assertIn("Physics Discussion", context)
        self.assertIn("0.80", context)  # Similarity score
    
    def test_format_context_empty(self):
        """Test formatting empty results."""
        from backend.chat.context_manager import format_context_for_llm
        
        context = format_context_for_llm([])
        
        self.assertIn("No relevant context", context)


class TestHistoryManagement(unittest.TestCase):
    """Test sliding window history management."""
    
    def test_apply_sliding_window_basic(self):
        """Test basic sliding window application."""
        from backend.chat.history_manager import apply_sliding_window
        
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What is physics?"},
        ]
        
        windowed = apply_sliding_window(messages, max_tokens=1000)
        
        # System message should always be included
        self.assertEqual(windowed[0]["role"], "system")
        # Should include recent messages
        self.assertGreater(len(windowed), 1)
    
    def test_apply_sliding_window_truncates(self):
        """Test that sliding window truncates old messages."""
        from backend.chat.history_manager import apply_sliding_window
        
        # Create many messages that exceed token limit
        messages = [
            {"role": "system", "content": "You are helpful."},
        ]
        for i in range(20):
            messages.append({"role": "user", "content": f"Message {i} " * 100})  # Large messages
            messages.append({"role": "assistant", "content": f"Response {i} " * 100})
        
        windowed = apply_sliding_window(messages, max_tokens=1000)
        
        # Should be much smaller than original
        self.assertLess(len(windowed), len(messages))
        # System message should still be first
        self.assertEqual(windowed[0]["role"], "system")
        # Should keep most recent messages (check last few messages for Message 19 or Response 19)
        recent_content = " ".join([msg.get("content", "") for msg in windowed[-4:]])
        self.assertIn("19", recent_content)  # Should contain message 19 or response 19


if __name__ == "__main__":
    unittest.main()
