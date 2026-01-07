"""
"Continue where I left off" feature.

Stores and retrieves the last opened conversation and scroll position.
"""
import sqlite3
from typing import Optional, Dict


DB_PATH = 'conversations.db'


def save_last_conversation(
    db_path: str,
    conversation_id: str,
    message_id: Optional[str] = None,
    scroll_offset: Optional[int] = None
) -> bool:
    """
    Save the last opened conversation and scroll position.
    
    Args:
        db_path: Database path
        conversation_id: Conversation ID
        message_id: Optional message ID (last visible message)
        scroll_offset: Optional pixel offset
    
    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO user_state 
            (key, conversation_id, message_id, scroll_offset, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', ('last_conversation', conversation_id, message_id, scroll_offset))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving last conversation: {e}")
        return False
    finally:
        conn.close()


def get_last_conversation(db_path: str) -> Optional[Dict]:
    """
    Get the last opened conversation and scroll position.
    
    Returns:
        Dict with conversation_id, message_id, scroll_offset, updated_at
        or None if not found
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('''
        SELECT conversation_id, message_id, scroll_offset, updated_at
        FROM user_state
        WHERE key = 'last_conversation'
        ORDER BY updated_at DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def clear_last_conversation(db_path: str) -> bool:
    """Clear the last conversation state."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM user_state WHERE key = 'last_conversation'
    ''')
    
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python continue_feature.py <command> [args...]")
        print("\nCommands:")
        print("  save <conversation_id> [message_id] [scroll_offset]")
        print("  get")
        print("  clear")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'save':
            conv_id = args[0]
            msg_id = args[1] if len(args) > 1 else None
            scroll = int(args[2]) if len(args) > 2 else None
            
            if save_last_conversation(DB_PATH, conv_id, msg_id, scroll):
                print(f"Saved last conversation: {conv_id}")
        
        elif command == 'get':
            state = get_last_conversation(DB_PATH)
            if state:
                print(f"Last conversation: {state['conversation_id']}")
                if state['message_id']:
                    print(f"  Message ID: {state['message_id']}")
                if state['scroll_offset']:
                    print(f"  Scroll offset: {state['scroll_offset']}")
                print(f"  Updated: {state['updated_at']}")
            else:
                print("No last conversation found")
        
        elif command == 'clear':
            if clear_last_conversation(DB_PATH):
                print("Cleared last conversation")
            else:
                print("No last conversation to clear")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

