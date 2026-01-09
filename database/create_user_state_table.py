"""
Create table for storing user state (last opened conversation, scroll position).
"""
import sqlite3


def create_user_state_table(db_path='conversations.db'):
    """Create table for user state storage."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            conversation_id TEXT,
            message_id TEXT,
            scroll_offset INTEGER,
            value_text TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_state_key 
        ON user_state(key)
    ''')
    
    conn.commit()
    conn.close()
    print(f"User state table created in {db_path}")


if __name__ == '__main__':
    create_user_state_table()

