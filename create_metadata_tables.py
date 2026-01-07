"""
Create database tables for storing conversation metadata.
"""

import sqlite3
from pathlib import Path


def create_metadata_tables(db_path='conversations.db'):
    """Create tables for storing conversation metadata."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Main metadata table - stores the JSON metadata blob
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            metadata_json TEXT NOT NULL,
            schema_version TEXT,
            model_used TEXT,
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        )
    ''')
    
    # Indexed fields table for faster queries
    # This stores extracted fields separately for efficient filtering/searching
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_metadata_indexed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            field_type TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT NOT NULL,
            evidence_message_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            UNIQUE(conversation_id, field_type, field_name, field_value)
        )
    ''')
    
    # Create indexes for fast queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_metadata_conversation_id 
        ON conversation_metadata(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_indexed_conversation_id 
        ON conversation_metadata_indexed(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_indexed_field_type 
        ON conversation_metadata_indexed(field_type)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_indexed_field_value 
        ON conversation_metadata_indexed(field_value)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Metadata tables created successfully in {db_path}")


if __name__ == '__main__':
    create_metadata_tables()

