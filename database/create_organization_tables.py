"""
Create database tables for organization features.

Features:
- Tags (user-defined) on conversations
- Folders / Projects (label table)
- Bookmarks (pin specific messages)
- Notes (user notes attached to convos/messages)
- Custom titles (override imported titles)
- Conversation relationships (merge/split/link)
"""
import sqlite3
from pathlib import Path


def create_organization_tables(db_path='conversations.db'):
    """Create tables for organization features."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tags table - user-defined tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Conversation tags (many-to-many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (tag_id) REFERENCES tags(tag_id),
            UNIQUE(conversation_id, tag_id)
        )
    ''')
    
    # Folders / Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            folder_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_folder_id INTEGER,
            color TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_folder_id) REFERENCES folders(folder_id)
        )
    ''')
    
    # Conversation folders (many-to-many, but typically one-to-one)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            folder_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (folder_id) REFERENCES folders(folder_id),
            UNIQUE(conversation_id, folder_id)
        )
    ''')
    
    # Bookmarks - pin specific messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            bookmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            message_id TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (conversation_id, message_id) REFERENCES messages(conversation_id, message_id)
        )
    ''')
    
    # Notes - user notes attached to conversations or messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            message_id TEXT,
            note_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (conversation_id, message_id) REFERENCES messages(conversation_id, message_id)
        )
    ''')
    
    # Custom titles - override imported titles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_titles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            custom_title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        )
    ''')
    
    # Conversation relationships - for merge/split/link
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id_1 TEXT NOT NULL,
            conversation_id_2 TEXT NOT NULL,
            relationship_type TEXT NOT NULL,  -- 'merged', 'split', 'related', 'duplicate'
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id_1) REFERENCES conversations(conversation_id),
            FOREIGN KEY (conversation_id_2) REFERENCES conversations(conversation_id),
            CHECK (conversation_id_1 != conversation_id_2)
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_tags_conv ON conversation_tags(conversation_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_tags_tag ON conversation_tags(tag_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_folders_conv ON conversation_folders(conversation_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_conv ON bookmarks(conversation_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_conv ON notes(conversation_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_conv1 ON conversation_relationships(conversation_id_1)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_conv2 ON conversation_relationships(conversation_id_2)')
    
    conn.commit()
    conn.close()
    print(f"Organization tables created successfully in {db_path}")


if __name__ == '__main__':
    create_organization_tables()

