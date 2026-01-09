"""
Comprehensive API endpoint testing for Lode MVP.
Tests all API endpoints programmatically.
"""
import requests
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import time

# API base URL
BASE_URL = "http://127.0.0.1:8000/api"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

def log_test(name: str, passed: bool, message: str = ""):
    """Log test result."""
    if passed:
        test_results["passed"].append(name)
        print(f"[PASS] {name}")
        if message:
            print(f"       {message}")
    else:
        test_results["failed"].append(name)
        print(f"[FAIL] {name}")
        if message:
            print(f"       {message}")

def skip_test(name: str, reason: str):
    """Skip a test."""
    test_results["skipped"].append(name)
    print(f"[SKIP] {name} - {reason}")

def check_server():
    """Check if API server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Server check error: {e}")
        return False

# ============================================================================
# 1. Database & Setup Tests
# ============================================================================

def test_health_check():
    """Test health check endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("Health Check", True, f"Status: {data.get('status')}")
            return True
        else:
            log_test("Health Check", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Health Check", False, str(e))
        return False

def test_setup_check():
    """Test setup check endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/setup/check", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("Setup Check", True, f"Initialized: {data.get('initialized')}")
            return data.get('initialized', False)
        else:
            log_test("Setup Check", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Setup Check", False, str(e))
        return False

# ============================================================================
# 2. Conversations API Tests
# ============================================================================

def test_list_conversations():
    """Test listing conversations."""
    try:
        response = requests.get(f"{BASE_URL}/conversations", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("List Conversations", True, f"Found {len(data)} conversations")
            return data
        else:
            log_test("List Conversations", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("List Conversations", False, str(e))
        return []

def test_list_conversations_sorted(sort_by: str):
    """Test listing conversations with sorting."""
    try:
        response = requests.get(f"{BASE_URL}/conversations?sort={sort_by}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test(f"List Conversations (sort={sort_by})", True, f"Found {len(data)} conversations")
            return data
        else:
            log_test(f"List Conversations (sort={sort_by})", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test(f"List Conversations (sort={sort_by})", False, str(e))
        return []

def test_get_conversation(conversation_id: str):
    """Test getting a single conversation."""
    try:
        response = requests.get(f"{BASE_URL}/conversations/{conversation_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Get Conversation ({conversation_id})", True)
            return data
        elif response.status_code == 404:
            log_test(f"Get Conversation ({conversation_id})", False, "Conversation not found")
            return None
        else:
            log_test(f"Get Conversation ({conversation_id})", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test(f"Get Conversation ({conversation_id})", False, str(e))
        return None

def test_get_messages(conversation_id: str):
    """Test getting messages for a conversation."""
    try:
        response = requests.get(f"{BASE_URL}/conversations/{conversation_id}/messages", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Get Messages ({conversation_id})", True, f"Found {len(data)} messages")
            return data
        elif response.status_code == 404:
            log_test(f"Get Messages ({conversation_id})", False, "Conversation not found")
            return []
        else:
            log_test(f"Get Messages ({conversation_id})", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test(f"Get Messages ({conversation_id})", False, str(e))
        return []

# ============================================================================
# 3. Search API Tests
# ============================================================================

def test_search(query: str):
    """Test search endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/search?q={query}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Search (query='{query}')", True, f"Found {len(data)} results")
            return data
        else:
            log_test(f"Search (query='{query}')", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test(f"Search (query='{query}')", False, str(e))
        return []

def test_search_with_limit(query: str, limit: int):
    """Test search with limit."""
    try:
        response = requests.get(f"{BASE_URL}/search?q={query}&limit={limit}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            actual_count = len(data)
            passed = actual_count <= limit
            log_test(f"Search with limit (limit={limit})", passed, f"Returned {actual_count} results")
            return data
        else:
            log_test(f"Search with limit (limit={limit})", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test(f"Search with limit (limit={limit})", False, str(e))
        return []

def test_get_message_context(message_id: str):
    """Test getting message context."""
    try:
        response = requests.get(f"{BASE_URL}/messages/{message_id}/context?n=5", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Get Message Context ({message_id})", True, f"Found {len(data)} messages")
            return data
        elif response.status_code == 404:
            log_test(f"Get Message Context ({message_id})", False, "Message not found")
            return []
        else:
            log_test(f"Get Message Context ({message_id})", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test(f"Get Message Context ({message_id})", False, str(e))
        return []

# ============================================================================
# 4. Organization API Tests
# ============================================================================

def test_add_tag(conversation_id: str, tag: str):
    """Test adding a tag."""
    try:
        response = requests.post(
            f"{BASE_URL}/conversations/{conversation_id}/tags",
            json={"name": tag},
            timeout=5
        )
        if response.status_code == 200:
            log_test(f"Add Tag ({tag})", True)
            return True
        else:
            log_test(f"Add Tag ({tag})", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test(f"Add Tag ({tag})", False, str(e))
        return False

def test_get_tags(conversation_id: str):
    """Test getting tags."""
    try:
        response = requests.get(f"{BASE_URL}/conversations/{conversation_id}/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Get Tags ({conversation_id})", True, f"Found {len(data)} tags")
            return data
        else:
            log_test(f"Get Tags ({conversation_id})", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test(f"Get Tags ({conversation_id})", False, str(e))
        return []

def test_remove_tag(conversation_id: str, tag: str):
    """Test removing a tag."""
    try:
        response = requests.delete(
            f"{BASE_URL}/conversations/{conversation_id}/tags/{tag}",
            timeout=5
        )
        if response.status_code == 200:
            log_test(f"Remove Tag ({tag})", True)
            return True
        else:
            log_test(f"Remove Tag ({tag})", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test(f"Remove Tag ({tag})", False, str(e))
        return False

def test_add_note(conversation_id: str, note_text: str):
    """Test adding a note."""
    try:
        response = requests.post(
            f"{BASE_URL}/conversations/{conversation_id}/notes",
            json={"note_text": note_text},
            timeout=5
        )
        if response.status_code == 200:
            log_test(f"Add Note", True)
            return True
        else:
            log_test(f"Add Note", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test(f"Add Note", False, str(e))
        return False

def test_get_notes(conversation_id: str):
    """Test getting notes."""
    try:
        response = requests.get(f"{BASE_URL}/conversations/{conversation_id}/notes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Get Notes ({conversation_id})", True, f"Found {len(data)} notes")
            return data
        else:
            log_test(f"Get Notes ({conversation_id})", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test(f"Get Notes ({conversation_id})", False, str(e))
        return []

def test_star_conversation(conversation_id: str):
    """Test starring a conversation."""
    try:
        response = requests.post(f"{BASE_URL}/conversations/{conversation_id}/star", timeout=5)
        if response.status_code == 200:
            log_test(f"Star Conversation ({conversation_id})", True)
            return True
        else:
            log_test(f"Star Conversation ({conversation_id})", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test(f"Star Conversation ({conversation_id})", False, str(e))
        return False

def test_unstar_conversation(conversation_id: str):
    """Test unstarring a conversation."""
    try:
        response = requests.delete(f"{BASE_URL}/conversations/{conversation_id}/star", timeout=5)
        if response.status_code == 200:
            log_test(f"Unstar Conversation ({conversation_id})", True)
            return True
        else:
            log_test(f"Unstar Conversation ({conversation_id})", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test(f"Unstar Conversation ({conversation_id})", False, str(e))
        return False

def test_set_custom_title(conversation_id: str, title: str):
    """Test setting custom title."""
    try:
        response = requests.put(
            f"{BASE_URL}/conversations/{conversation_id}/title",
            json={"title": title},
            timeout=5
        )
        if response.status_code == 200:
            log_test(f"Set Custom Title", True)
            return True
        else:
            log_test(f"Set Custom Title", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test(f"Set Custom Title", False, str(e))
        return False

# ============================================================================
# 5. Find Tools API Tests
# ============================================================================

def test_find_code():
    """Test find code blocks."""
    try:
        response = requests.get(f"{BASE_URL}/find/code", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Find Code Blocks", True, f"Found {len(data)} code blocks")
            return data
        else:
            log_test("Find Code Blocks", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("Find Code Blocks", False, str(e))
        return []

def test_find_links():
    """Test find links."""
    try:
        response = requests.get(f"{BASE_URL}/find/links", timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Handle both array and dict responses
            if isinstance(data, dict):
                data = data.get('links', [])
            log_test("Find Links", True, f"Found {len(data)} links")
            return data
        else:
            log_test("Find Links", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("Find Links", False, str(e))
        return []

def test_find_todos():
    """Test find TODOs."""
    try:
        response = requests.get(f"{BASE_URL}/find/todos", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Find TODOs", True, f"Found {len(data)} TODOs")
            return data
        else:
            log_test("Find TODOs", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("Find TODOs", False, str(e))
        return []

def test_find_questions():
    """Test find questions."""
    try:
        response = requests.get(f"{BASE_URL}/find/questions", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Find Questions", True, f"Found {len(data)} questions")
            return data
        else:
            log_test("Find Questions", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("Find Questions", False, str(e))
        return []

def test_find_dates():
    """Test find dates."""
    try:
        response = requests.get(f"{BASE_URL}/find/dates", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Find Dates", True, f"Found {len(data)} dates")
            return data
        else:
            log_test("Find Dates", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("Find Dates", False, str(e))
        return []

def test_find_decisions():
    """Test find decisions."""
    try:
        response = requests.get(f"{BASE_URL}/find/decisions", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Find Decisions", True, f"Found {len(data)} decisions")
            return data
        else:
            log_test("Find Decisions", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("Find Decisions", False, str(e))
        return []

def test_find_prompts():
    """Test find prompts."""
    try:
        response = requests.get(f"{BASE_URL}/find/prompts", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Find Prompts", True, f"Found {len(data)} prompts")
            return data
        else:
            log_test("Find Prompts", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("Find Prompts", False, str(e))
        return []

# ============================================================================
# 6. Analytics API Tests
# ============================================================================

def test_analytics_usage(period: str = "day"):
    """Test usage analytics."""
    try:
        response = requests.get(f"{BASE_URL}/analytics/usage?period={period}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Analytics Usage (period={period})", True)
            return data
        else:
            log_test(f"Analytics Usage (period={period})", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test(f"Analytics Usage (period={period})", False, str(e))
        return None

def test_analytics_streaks():
    """Test streaks analytics."""
    try:
        response = requests.get(f"{BASE_URL}/analytics/streaks", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Analytics Streaks", True)
            return data
        else:
            log_test("Analytics Streaks", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Analytics Streaks", False, str(e))
        return None

def test_analytics_words(limit: int = 10):
    """Test words analytics."""
    try:
        response = requests.get(f"{BASE_URL}/analytics/top-words?limit={limit}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Analytics Words (limit={limit})", True, f"Found {len(data)} words")
            return data
        else:
            log_test(f"Analytics Words (limit={limit})", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test(f"Analytics Words (limit={limit})", False, str(e))
        return None

def test_analytics_phrases(limit: int = 10):
    """Test phrases analytics."""
    try:
        response = requests.get(f"{BASE_URL}/analytics/top-phrases?limit={limit}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Analytics Phrases (limit={limit})", True, f"Found {len(data)} phrases")
            return data
        else:
            log_test(f"Analytics Phrases (limit={limit})", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test(f"Analytics Phrases (limit={limit})", False, str(e))
        return None

def test_analytics_vocabulary():
    """Test vocabulary analytics."""
    try:
        response = requests.get(f"{BASE_URL}/analytics/vocabulary", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Analytics Vocabulary", True)
            return data
        else:
            log_test("Analytics Vocabulary", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Analytics Vocabulary", False, str(e))
        return None

def test_analytics_ratios():
    """Test ratios analytics."""
    try:
        response = requests.get(f"{BASE_URL}/analytics/response-ratio", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Analytics Ratios", True)
            return data
        else:
            log_test("Analytics Ratios", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Analytics Ratios", False, str(e))
        return None

def test_analytics_heatmap():
    """Test heatmap analytics."""
    try:
        response = requests.get(f"{BASE_URL}/analytics/heatmap", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("Analytics Heatmap", True)
            return data
        else:
            log_test("Analytics Heatmap", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Analytics Heatmap", False, str(e))
        return None

# ============================================================================
# 7. Export API Tests
# ============================================================================

def test_export_conversation(conversation_id: str, format: str = "markdown"):
    """Test exporting a conversation."""
    try:
        response = requests.post(
            f"{BASE_URL}/export/conversation/{conversation_id}",
            params={"format": format, "include_timestamps": True, "include_metadata": True},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            log_test(f"Export Conversation ({format})", True, f"Exported {len(data.get('content', ''))} chars")
            return data
        else:
            log_test(f"Export Conversation ({format})", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test(f"Export Conversation ({format})", False, str(e))
        return None

# ============================================================================
# 8. Settings & Management API Tests
# ============================================================================

def test_integrity_checks():
    """Test integrity checks."""
    try:
        response = requests.get(f"{BASE_URL}/integrity/check", timeout=30)
        if response.status_code == 200:
            data = response.json()
            log_test("Integrity Checks", True)
            return data
        else:
            log_test("Integrity Checks", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Integrity Checks", False, str(e))
        return None

def test_deduplication():
    """Test deduplication."""
    try:
        response = requests.get(f"{BASE_URL}/deduplication/find-conversations", timeout=30)
        if response.status_code == 200:
            data = response.json()
            log_test("Deduplication", True)
            return data
        else:
            log_test("Deduplication", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Deduplication", False, str(e))
        return None

# ============================================================================
# 9. Job System Tests
# ============================================================================

def test_list_jobs():
    """Test listing jobs."""
    try:
        response = requests.get(f"{BASE_URL}/jobs", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("List Jobs", True, f"Found {len(data)} jobs")
            return data
        else:
            log_test("List Jobs", False, f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("List Jobs", False, str(e))
        return []

def test_get_job(job_id: str):
    """Test getting a job."""
    try:
        response = requests.get(f"{BASE_URL}/jobs/{job_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test(f"Get Job ({job_id})", True, f"Status: {data.get('status')}")
            return data
        else:
            log_test(f"Get Job ({job_id})", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test(f"Get Job ({job_id})", False, str(e))
        return None

# ============================================================================
# 10. State Management Tests
# ============================================================================

def test_get_state():
    """Test getting state."""
    try:
        response = requests.get(f"{BASE_URL}/state", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("Get State", True)
            return data
        else:
            log_test("Get State", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Get State", False, str(e))
        return None

def test_save_state(conversation_id: str):
    """Test saving state."""
    try:
        response = requests.post(
            f"{BASE_URL}/state",
            json={"last_conversation_id": conversation_id},
            timeout=5
        )
        if response.status_code == 200:
            log_test("Save State", True)
            return True
        else:
            log_test("Save State", False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Save State", False, str(e))
        return False

# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all API tests."""
    print("=" * 70)
    print("Lode MVP - API Endpoint Testing")
    print("=" * 70)
    print()
    
    # Check if server is running
    print("Checking if API server is running...")
    if not check_server():
        print("[ERROR] API server is not running!")
        print("        Please start the backend server first.")
        print("        Run: python -m backend.main")
        return
    print("[OK] API server is running")
    print()
    
    # 1. Database & Setup
    print("=" * 70)
    print("1. Database & Setup Tests")
    print("=" * 70)
    test_health_check()
    initialized = test_setup_check()
    print()
    
    if not initialized:
        print("[WARN] Database not initialized. Some tests may fail.")
        print()
    
    # 2. Conversations API
    print("=" * 70)
    print("2. Conversations API Tests")
    print("=" * 70)
    conversations = test_list_conversations()
    test_list_conversations_sorted("newest")
    test_list_conversations_sorted("oldest")
    test_list_conversations_sorted("longest")
    test_list_conversations_sorted("most_messages")
    
    # Test with first conversation if available
    if conversations:
        conv_id = conversations[0].get('conversation_id')
        if conv_id:
            test_get_conversation(conv_id)
            messages = test_get_messages(conv_id)
            if messages:
                msg_id = messages[0].get('message_id')
                if msg_id:
                    test_get_message_context(msg_id)
    print()
    
    # 3. Search API
    print("=" * 70)
    print("3. Search API Tests")
    print("=" * 70)
    test_search("test")
    test_search_with_limit("test", 5)
    print()
    
    # 4. Organization API
    print("=" * 70)
    print("4. Organization API Tests")
    print("=" * 70)
    if conversations:
        conv_id = conversations[0].get('conversation_id')
        if conv_id:
            test_add_tag(conv_id, "test-tag")
            test_get_tags(conv_id)
            test_remove_tag(conv_id, "test-tag")
            test_add_note(conv_id, "Test note from API testing")
            test_get_notes(conv_id)
            test_star_conversation(conv_id)
            test_unstar_conversation(conv_id)
            test_set_custom_title(conv_id, "Test Custom Title")
    print()
    
    # 5. Find Tools API
    print("=" * 70)
    print("5. Find Tools API Tests")
    print("=" * 70)
    test_find_code()
    test_find_links()
    test_find_todos()
    test_find_questions()
    test_find_dates()
    test_find_decisions()
    test_find_prompts()
    print()
    
    # 6. Analytics API
    print("=" * 70)
    print("6. Analytics API Tests")
    print("=" * 70)
    test_analytics_usage("day")
    test_analytics_usage("week")
    test_analytics_usage("month")
    test_analytics_streaks()
    test_analytics_words(10)
    test_analytics_phrases(10)
    test_analytics_vocabulary()
    test_analytics_ratios()
    test_analytics_heatmap()
    print()
    
    # 7. Export API
    print("=" * 70)
    print("7. Export API Tests")
    print("=" * 70)
    if conversations:
        conv_id = conversations[0].get('conversation_id')
        if conv_id:
            test_export_conversation(conv_id, "markdown")
            test_export_conversation(conv_id, "json")
            test_export_conversation(conv_id, "csv")
    print()
    
    # 8. Settings & Management API
    print("=" * 70)
    print("8. Settings & Management API Tests")
    print("=" * 70)
    test_integrity_checks()
    test_deduplication()
    print()
    
    # 9. Job System
    print("=" * 70)
    print("9. Job System Tests")
    print("=" * 70)
    jobs = test_list_jobs()
    if jobs:
        job_id = jobs[0].get('id')
        if job_id:
            test_get_job(job_id)
    print()
    
    # 10. State Management
    print("=" * 70)
    print("10. State Management Tests")
    print("=" * 70)
    test_get_state()
    if conversations:
        conv_id = conversations[0].get('conversation_id')
        if conv_id:
            test_save_state(conv_id)
    print()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    total = len(test_results["passed"]) + len(test_results["failed"]) + len(test_results["skipped"])
    print(f"Total Tests: {total}")
    print(f"[PASS] Passed: {len(test_results['passed'])}")
    print(f"[FAIL] Failed: {len(test_results['failed'])}")
    print(f"[SKIP] Skipped: {len(test_results['skipped'])}")
    print()
    
    if test_results["failed"]:
        print("Failed Tests:")
        for test in test_results["failed"]:
            print(f"  - {test}")
        print()
    
    if test_results["skipped"]:
        print("Skipped Tests:")
        for test in test_results["skipped"]:
            print(f"  - {test}")
        print()
    
    success_rate = (len(test_results["passed"]) / total * 100) if total > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print()

if __name__ == "__main__":
    run_all_tests()

