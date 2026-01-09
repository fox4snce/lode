"""
Tests for "Continue where I left off" feature.
"""
import sqlite3
import os
import tempfile
from continue_feature import (
    save_last_conversation,
    get_last_conversation,
    clear_last_conversation
)


def test_save_and_get_last_conversation():
    """Test saving and retrieving last conversation."""
    # Create temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Create tables
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        database_dir = project_root / "database"
        if str(database_dir) not in sys.path:
            sys.path.insert(0, str(database_dir))
        from create_database import create_database
        from create_user_state_table import create_user_state_table
        
        create_database(db_path)
        create_user_state_table(db_path)
        
        # Insert test conversation
        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO conversations (conversation_id, title)
            VALUES (?, ?)
        ''', ('test-conv-001', 'Test Conversation'))
        conn.commit()
        conn.close()
        
        # Save last conversation
        save_last_conversation(db_path, 'test-conv-001', message_id='msg-001', scroll_offset=100)
        
        # Retrieve it
        state = get_last_conversation(db_path)
        
        assert state is not None
        assert state['conversation_id'] == 'test-conv-001'
        assert state['message_id'] == 'msg-001'
        assert state['scroll_offset'] == 100
        
        print("[PASS] test_save_and_get_last_conversation")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_update_last_conversation():
    """Test updating last conversation."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        from create_database import create_database
        from create_user_state_table import create_user_state_table
        
        create_database(db_path)
        create_user_state_table(db_path)
        
        conn = sqlite3.connect(db_path)
        conn.execute('INSERT INTO conversations (conversation_id, title) VALUES (?, ?)', 
                     ('test-conv-001', 'Test 1'))
        conn.execute('INSERT INTO conversations (conversation_id, title) VALUES (?, ?)', 
                     ('test-conv-002', 'Test 2'))
        conn.commit()
        conn.close()
        
        # Save first conversation
        save_last_conversation(db_path, 'test-conv-001', message_id='msg-001')
        
        # Update to second conversation
        save_last_conversation(db_path, 'test-conv-002', message_id='msg-002')
        
        # Verify update
        state = get_last_conversation(db_path)
        assert state['conversation_id'] == 'test-conv-002'
        assert state['message_id'] == 'msg-002'
        
        print("[PASS] test_update_last_conversation")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_clear_last_conversation():
    """Test clearing last conversation."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        from create_database import create_database
        from create_user_state_table import create_user_state_table
        
        create_database(db_path)
        create_user_state_table(db_path)
        
        conn = sqlite3.connect(db_path)
        conn.execute('INSERT INTO conversations (conversation_id, title) VALUES (?, ?)', 
                     ('test-conv-001', 'Test'))
        conn.commit()
        conn.close()
        
        # Save and then clear
        save_last_conversation(db_path, 'test-conv-001')
        clear_last_conversation(db_path)
        
        # Verify cleared
        state = get_last_conversation(db_path)
        assert state is None or state.get('conversation_id') is None
        
        print("[PASS] test_clear_last_conversation")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    test_save_and_get_last_conversation()
    test_update_last_conversation()
    test_clear_last_conversation()
    print("\nAll tests passed!")

