"""
Tests for deduplication tool.
"""
import sqlite3
import os
import tempfile
import hashlib
from deduplication_tool import (
    normalize_content,
    hash_content,
    find_duplicate_messages,
    mark_duplicate_messages,
    find_duplicate_conversations
)


def test_normalize_content():
    """Test content normalization."""
    text1 = "Hello   World\n\nTest"
    text2 = "hello world test"
    text3 = "  Hello World  Test  "
    
    norm1 = normalize_content(text1)
    norm2 = normalize_content(text2)
    norm3 = normalize_content(text3)
    
    assert norm1 == norm2 == norm3
    print("[PASS] test_normalize_content")


def test_hash_content():
    """Test content hashing."""
    text = "Test content"
    hash1 = hash_content(text)
    hash2 = hash_content(text)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex length
    
    # Different content should have different hash
    hash3 = hash_content("Different content")
    assert hash1 != hash3
    
    print("[PASS] test_hash_content")


def test_find_duplicate_messages():
    """Test finding duplicate messages."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        from create_database import create_database
        from create_deduplication_tables import create_deduplication_tables
        
        create_database(db_path)
        create_deduplication_tables(db_path)
        
        conn = sqlite3.connect(db_path)
        # Create test conversation
        conn.execute('''
            INSERT INTO conversations (conversation_id, title)
            VALUES (?, ?)
        ''', ('test-conv-001', 'Test'))
        
        # Insert duplicate messages
        conn.execute('''
            INSERT INTO messages (conversation_id, message_id, role, content)
            VALUES (?, ?, ?, ?)
        ''', ('test-conv-001', 'msg-001', 'user', 'Hello world'))
        
        conn.execute('''
            INSERT INTO messages (conversation_id, message_id, role, content)
            VALUES (?, ?, ?, ?)
        ''', ('test-conv-001', 'msg-002', 'user', 'Hello world'))  # Duplicate
        
        conn.execute('''
            INSERT INTO messages (conversation_id, message_id, role, content)
            VALUES (?, ?, ?, ?)
        ''', ('test-conv-001', 'msg-003', 'user', 'Different content'))
        
        conn.commit()
        
        # Hash all messages
        from deduplication_tool import hash_all_messages
        hash_all_messages(db_path, 'test-conv-001')
        
        # Find duplicates
        duplicates = find_duplicate_messages(db_path, 'test-conv-001')
        
        # Should find msg-001 and msg-002 as duplicates
        found_duplicate = False
        for group in duplicates:
            if group['count'] >= 2:
                msg_ids = [m['message_id'] for m in group['messages']]
                if 'msg-001' in msg_ids and 'msg-002' in msg_ids:
                    found_duplicate = True
                    break
        
        assert found_duplicate, f"Expected to find duplicates, got: {duplicates}"
        
        conn.close()
        print("[PASS] test_find_duplicate_messages")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    test_normalize_content()
    test_hash_content()
    test_find_duplicate_messages()
    print("\nAll deduplication tests passed!")

