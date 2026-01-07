"""
Create database tables for storing entities and keywords extracted from conversations.
"""

import sqlite3


def create_entity_keyword_tables(db_path='conversations.db'):
    """Create tables for storing entities and keywords."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Canonical entity dictionary
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_text TEXT UNIQUE NOT NULL,
            preferred_display_text TEXT NOT NULL,
            entity_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Many-to-many join: conversations <-> entities
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            count INTEGER DEFAULT 1,
            example_spans TEXT,
            surface_forms TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
            UNIQUE(conversation_id, entity_id)
        )
    ''')
    
    # Canonical keyword/keyphrase dictionary
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_phrase TEXT UNIQUE NOT NULL,
            preferred_display_phrase TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Many-to-many join: conversations <-> keywords
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            keyword_id INTEGER NOT NULL,
            score REAL,
            rank INTEGER,
            source TEXT DEFAULT 'keybert',
            method_config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id),
            UNIQUE(conversation_id, keyword_id)
        )
    ''')
    
    # Embeddings cache to avoid recomputation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS embedding_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_hash TEXT UNIQUE NOT NULL,
            model TEXT NOT NULL,
            vector BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(text_hash, model)
        )
    ''')
    
    # Create indexes for fast queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_entities_canonical 
        ON entities(canonical_text)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_entities_conv 
        ON conversation_entities(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_entities_entity 
        ON conversation_entities(entity_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_keywords_canonical 
        ON keywords(canonical_phrase)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_keywords_conv 
        ON conversation_keywords(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_keywords_keyword 
        ON conversation_keywords(keyword_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_keywords_rank 
        ON conversation_keywords(conversation_id, rank)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash 
        ON embedding_cache(text_hash)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Entity and keyword tables created successfully: {db_path}")


if __name__ == '__main__':
    create_entity_keyword_tables()

