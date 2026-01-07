import sqlite3
from pathlib import Path

def create_database(db_path='conversations.db'):
    """Create the SQLite database with conversations and messages tables."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table: conversations - metadata about each conversation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            title TEXT,
            create_time REAL,
            update_time REAL,
            is_archived INTEGER DEFAULT 0,
            is_starred INTEGER DEFAULT 0,
            default_model_slug TEXT,
            conversation_origin TEXT,
            ai_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index on conversation_id for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_id 
        ON conversations(conversation_id)
    ''')
    
    # Create index on create_time for date filtering
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_create_time 
        ON conversations(create_time)
    ''')
    
    # Table: messages - individual messages within conversations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            parent_id TEXT,
            role TEXT,
            content TEXT,
            create_time REAL,
            weight REAL,
            status TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            UNIQUE(conversation_id, message_id)
        )
    ''')
    
    # Create indexes for messages
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_conversation 
        ON messages(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_parent 
        ON messages(parent_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_create_time 
        ON messages(create_time)
    ''')
    
    # Table: conversation_descriptions - for future use (as mentioned by user)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_descriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            UNIQUE(conversation_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database created successfully: {db_path}")

if __name__ == '__main__':
    create_database()

