"""
Integrity checks for conversation data.

Detects broken thread ordering, missing timestamps, and other data issues.
"""
import sqlite3
from typing import Dict, List
from datetime import datetime


DB_PATH = 'conversations.db'


def check_missing_timestamps(db_path: str) -> Dict:
    """Check for missing timestamps in conversations and messages."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Check conversations
    cursor = conn.execute('''
        SELECT conversation_id, title
        FROM conversations
        WHERE create_time IS NULL
    ''')
    conversations = [dict(row) for row in cursor.fetchall()]
    
    # Check messages
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role
        FROM messages
        WHERE create_time IS NULL
    ''')
    messages = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'conversations': conversations,
        'messages': messages,
        'count': len(conversations) + len(messages)
    }


def check_broken_threads(db_path: str) -> List[Dict]:
    """Check for messages with parent_id that doesn't exist."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT m.conversation_id, m.message_id, m.parent_id
        FROM messages m
        LEFT JOIN messages parent ON 
            parent.conversation_id = m.conversation_id 
            AND parent.message_id = m.parent_id
        WHERE m.parent_id IS NOT NULL
            AND parent.message_id IS NULL
    ''')
    
    broken = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return broken


def check_orphaned_messages(db_path: str) -> List[Dict]:
    """Check for messages with conversation_id that doesn't exist."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT m.conversation_id, m.message_id, m.role
        FROM messages m
        LEFT JOIN conversations c ON c.conversation_id = m.conversation_id
        WHERE c.conversation_id IS NULL
    ''')
    
    orphaned = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orphaned


def check_duplicate_ids(db_path: str) -> Dict:
    """Check for duplicate conversation_ids and message_ids."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Duplicate conversation_ids
    cursor = conn.execute('''
        SELECT conversation_id, COUNT(*) as count
        FROM conversations
        GROUP BY conversation_id
        HAVING COUNT(*) > 1
    ''')
    duplicate_conversations = [dict(row) for row in cursor.fetchall()]
    
    # Duplicate (conversation_id, message_id) pairs
    cursor = conn.execute('''
        SELECT conversation_id, message_id, COUNT(*) as count
        FROM messages
        GROUP BY conversation_id, message_id
        HAVING COUNT(*) > 1
    ''')
    duplicate_messages = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'conversations': duplicate_conversations,
        'messages': duplicate_messages
    }


def check_invalid_timestamps(db_path: str) -> Dict:
    """Check for invalid timestamps (future dates or before 2000)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    now = datetime.now().timestamp()
    year_2000 = datetime(2000, 1, 1).timestamp()
    
    # Invalid conversation timestamps
    cursor = conn.execute('''
        SELECT conversation_id, title, create_time
        FROM conversations
        WHERE create_time IS NOT NULL
            AND (create_time > ? OR create_time < ?)
    ''', (now, year_2000))
    invalid_conversations = [dict(row) for row in cursor.fetchall()]
    
    # Invalid message timestamps
    cursor = conn.execute('''
        SELECT conversation_id, message_id, create_time
        FROM messages
        WHERE create_time IS NOT NULL
            AND (create_time > ? OR create_time < ?)
    ''', (now, year_2000))
    invalid_messages = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'conversations': invalid_conversations,
        'messages': invalid_messages
    }


def check_empty_content(db_path: str) -> List[Dict]:
    """Check for messages with NULL or empty content."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role
        FROM messages
        WHERE content IS NULL OR content = ''
    ''')
    
    empty = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return empty


def check_missing_roles(db_path: str) -> List[Dict]:
    """Check for messages without role field."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id
        FROM messages
        WHERE role IS NULL OR role = ''
    ''')
    
    missing = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return missing


def check_integrity(db_path: str) -> Dict:
    """
    Run all integrity checks and return summary.
    
    Returns:
        Dict with all check results and summary statistics
    """
    results = {
        'missing_timestamps': check_missing_timestamps(db_path),
        'broken_threads': check_broken_threads(db_path),
        'orphaned_messages': check_orphaned_messages(db_path),
        'duplicate_ids': check_duplicate_ids(db_path),
        'invalid_timestamps': check_invalid_timestamps(db_path),
        'empty_content': check_empty_content(db_path),
        'missing_roles': check_missing_roles(db_path)
    }
    
    # Calculate summary
    summary = {
        'total_issues': (
            results['missing_timestamps']['count'] +
            len(results['broken_threads']) +
            len(results['orphaned_messages']) +
            len(results['duplicate_ids']['conversations']) +
            len(results['duplicate_ids']['messages']) +
            len(results['invalid_timestamps']['conversations']) +
            len(results['invalid_timestamps']['messages']) +
            len(results['empty_content']) +
            len(results['missing_roles'])
        ),
        'has_issues': False
    }
    
    summary['has_issues'] = summary['total_issues'] > 0
    
    results['summary'] = summary
    return results


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python integrity_checks.py <command>")
        print("\nCommands:")
        print("  all - Run all checks")
        print("  missing-timestamps")
        print("  broken-threads")
        print("  orphaned-messages")
        print("  duplicate-ids")
        print("  invalid-timestamps")
        print("  empty-content")
        print("  missing-roles")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == 'all':
            results = check_integrity(DB_PATH)
            summary = results['summary']
            print(f"Integrity Check Summary:")
            print(f"  Total issues: {summary['total_issues']}")
            print(f"  Has issues: {summary['has_issues']}")
            print(f"\nDetails:")
            print(f"  Missing timestamps: {results['missing_timestamps']['count']}")
            print(f"  Broken threads: {len(results['broken_threads'])}")
            print(f"  Orphaned messages: {len(results['orphaned_messages'])}")
            print(f"  Duplicate conversations: {len(results['duplicate_ids']['conversations'])}")
            print(f"  Duplicate messages: {len(results['duplicate_ids']['messages'])}")
            print(f"  Invalid timestamps: {len(results['invalid_timestamps']['conversations']) + len(results['invalid_timestamps']['messages'])}")
            print(f"  Empty content: {len(results['empty_content'])}")
            print(f"  Missing roles: {len(results['missing_roles'])}")
        
        elif command == 'missing-timestamps':
            issues = check_missing_timestamps(DB_PATH)
            print(f"Missing Timestamps:")
            print(f"  Conversations: {len(issues['conversations'])}")
            print(f"  Messages: {len(issues['messages'])}")
        
        elif command == 'broken-threads':
            broken = check_broken_threads(DB_PATH)
            print(f"Broken Threads: {len(broken)}")
            for b in broken[:5]:
                print(f"  {b['conversation_id']}/{b['message_id']} -> parent {b['parent_id']} not found")
        
        elif command == 'orphaned-messages':
            orphaned = check_orphaned_messages(DB_PATH)
            print(f"Orphaned Messages: {len(orphaned)}")
            for o in orphaned[:5]:
                print(f"  {o['conversation_id']}/{o['message_id']}")
        
        elif command == 'duplicate-ids':
            duplicates = check_duplicate_ids(DB_PATH)
            print(f"Duplicate IDs:")
            print(f"  Conversations: {len(duplicates['conversations'])}")
            print(f"  Messages: {len(duplicates['messages'])}")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

