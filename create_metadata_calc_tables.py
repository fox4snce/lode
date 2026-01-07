"""
Create tables for storing calculated conversation metadata.

Stores pre-calculated stats to avoid recomputing:
- Message counts (total, user, assistant, system)
- Character/word counts per conversation and per speaker
- Conversation duration
- Active days
- Average/max message length
- Attachment/link counts
"""
import sqlite3
from pathlib import Path


def create_metadata_calc_tables(db_path='conversations.db'):
    """Create tables for calculated conversation metadata."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Calculated metadata table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            
            -- Message counts
            message_count_total INTEGER DEFAULT 0,
            message_count_user INTEGER DEFAULT 0,
            message_count_assistant INTEGER DEFAULT 0,
            message_count_system INTEGER DEFAULT 0,
            
            -- Character/word counts (total)
            character_count_total INTEGER DEFAULT 0,
            word_count_total INTEGER DEFAULT 0,
            
            -- Character/word counts by role
            character_count_user INTEGER DEFAULT 0,
            word_count_user INTEGER DEFAULT 0,
            character_count_assistant INTEGER DEFAULT 0,
            word_count_assistant INTEGER DEFAULT 0,
            character_count_system INTEGER DEFAULT 0,
            word_count_system INTEGER DEFAULT 0,
            
            -- Timing
            first_message_time REAL,
            last_message_time REAL,
            duration_seconds REAL,
            active_days INTEGER DEFAULT 0,
            
            -- Message length stats
            avg_message_length REAL,
            max_message_length INTEGER DEFAULT 0,
            
            -- Content analysis
            url_count INTEGER DEFAULT 0,
            code_block_count INTEGER DEFAULT 0,
            file_path_count INTEGER DEFAULT 0,
            
            -- Model/provider info (from import)
            model_name TEXT,
            provider TEXT,
            
            -- Timestamps
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_conv ON conversation_stats(conversation_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_message_count ON conversation_stats(message_count_total)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_duration ON conversation_stats(duration_seconds)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_active_days ON conversation_stats(active_days)')
    
    conn.commit()
    conn.close()
    print(f"Metadata calculation tables created successfully in {db_path}")


if __name__ == '__main__':
    create_metadata_calc_tables()

