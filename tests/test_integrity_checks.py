"""
Tests for integrity checks.
"""
import sqlite3
import os
import tempfile
from integrity_checks import (
    check_integrity,
    check_missing_timestamps,
    check_broken_threads,
    check_orphaned_messages
)


def test_check_missing_timestamps():
    """Test missing timestamp detection."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        database_dir = project_root / "database"
        if str(database_dir) not in sys.path:
            sys.path.insert(0, str(database_dir))
        from create_database import create_database
        create_database(db_path)
        
        conn = sqlite3.connect(db_path)
        # Create conversation with missing timestamp
        conn.execute('''
            INSERT INTO conversations (conversation_id, title)
            VALUES (?, ?)
        ''', ('test-conv-001', 'Test'))
        
        # Create message with missing timestamp
        conn.execute('''
            INSERT INTO messages (conversation_id, message_id, role, content)
            VALUES (?, ?, ?, ?)
        ''', ('test-conv-001', 'msg-001', 'user', 'Hello'))
        
        conn.commit()
        conn.close()
        
        # Check for missing timestamps
        issues = check_missing_timestamps(db_path)
        
        # Should find missing timestamps
        assert len(issues['conversations']) > 0 or len(issues['messages']) > 0
        
        print("[PASS] test_check_missing_timestamps")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_check_orphaned_messages():
    """Test orphaned message detection."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        database_dir = project_root / "database"
        if str(database_dir) not in sys.path:
            sys.path.insert(0, str(database_dir))
        from create_database import create_database
        create_database(db_path)
        
        conn = sqlite3.connect(db_path)
        # Create orphaned message (conversation doesn't exist)
        conn.execute('''
            INSERT INTO messages (conversation_id, message_id, role, content)
            VALUES (?, ?, ?, ?)
        ''', ('nonexistent-conv', 'msg-001', 'user', 'Hello'))
        
        conn.commit()
        conn.close()
        
        # Check for orphaned messages
        orphaned = check_orphaned_messages(db_path)
        
        assert len(orphaned) > 0
        assert orphaned[0]['conversation_id'] == 'nonexistent-conv'
        
        print("[PASS] test_check_orphaned_messages")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    test_check_missing_timestamps()
    test_check_orphaned_messages()
    print("\nAll integrity check tests passed!")

