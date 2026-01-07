"""
Create tables for deduplication tracking.
"""
import sqlite3


def create_deduplication_tables(db_path='conversations.db'):
    """Create tables for message and conversation deduplication."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Message hashes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            is_duplicate INTEGER DEFAULT 0,
            original_message_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id, message_id) 
                REFERENCES messages(conversation_id, message_id),
            FOREIGN KEY (conversation_id, original_message_id) 
                REFERENCES messages(conversation_id, message_id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_message_hash_content 
        ON message_hashes(content_hash)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_message_hash_conversation 
        ON message_hashes(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_message_hash_duplicate 
        ON message_hashes(is_duplicate)
    ''')
    
    # Conversation hashes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            content_hash TEXT NOT NULL,
            is_duplicate INTEGER DEFAULT 0,
            original_conversation_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (original_conversation_id) REFERENCES conversations(conversation_id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_hash_content 
        ON conversation_hashes(content_hash)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Deduplication tables created in {db_path}")


if __name__ == '__main__':
    create_deduplication_tables()

