"""
Create SQLite FTS5 full-text search tables.

FTS5 provides:
- Phrase search
- AND/OR operators
- Exclude words (NOT)
- Prefix search
"""
import sqlite3
from pathlib import Path


def create_fts5_tables(db_path='conversations.db'):
    """Create FTS5 virtual tables for full-text search."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # FTS5 table for messages (content search)
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            conversation_id UNINDEXED,
            message_id UNINDEXED,
            role UNINDEXED,
            content,
            create_time UNINDEXED,
            content='messages',
            content_rowid='id'
        )
    ''')
    
    # FTS5 table for conversations (title search)
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
            conversation_id UNINDEXED,
            title,
            create_time UNINDEXED,
            content='conversations',
            content_rowid='id'
        )
    ''')
    
    # Populate FTS5 tables with existing data
    print("Populating FTS5 tables with existing data...")
    
    # Check if tables already have data and rebuild if needed
    cursor.execute("SELECT COUNT(*) FROM messages_fts")
    existing_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE content IS NOT NULL")
    total_messages = cursor.fetchone()[0]
    
    # If counts don't match or table is empty, rebuild
    if existing_messages != total_messages:
        print(f"  Rebuilding messages_fts (existing: {existing_messages}, total: {total_messages})")
        cursor.execute("DELETE FROM messages_fts")
        cursor.execute('''
            INSERT INTO messages_fts(conversation_id, message_id, role, content, create_time)
            SELECT conversation_id, message_id, role, content, create_time
            FROM messages
            WHERE content IS NOT NULL
        ''')
        print(f"  Indexed {cursor.rowcount} messages")
    else:
        print(f"  messages_fts already populated ({existing_messages} messages)")
    
    cursor.execute("SELECT COUNT(*) FROM conversations_fts")
    existing_convs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversations")
    total_convs = cursor.fetchone()[0]
    
    # If counts don't match or table is empty, rebuild
    if existing_convs != total_convs:
        print(f"  Rebuilding conversations_fts (existing: {existing_convs}, total: {total_convs})")
        cursor.execute("DELETE FROM conversations_fts")
        cursor.execute('''
            INSERT INTO conversations_fts(conversation_id, title, create_time)
            SELECT conversation_id, COALESCE(title, ''), create_time
            FROM conversations
        ''')
        print(f"  Indexed {cursor.rowcount} conversations")
    else:
        print(f"  conversations_fts already populated ({existing_convs} conversations)")
    
    # Create triggers to keep FTS5 in sync with main tables
    # Messages trigger
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(conversation_id, message_id, role, content, create_time)
            VALUES (new.conversation_id, new.message_id, new.role, new.content, new.create_time);
        END
    ''')
    
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
            DELETE FROM messages_fts WHERE message_id = old.message_id AND conversation_id = old.conversation_id;
        END
    ''')
    
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
            DELETE FROM messages_fts WHERE message_id = old.message_id AND conversation_id = old.conversation_id;
            INSERT INTO messages_fts(conversation_id, message_id, role, content, create_time)
            VALUES (new.conversation_id, new.message_id, new.role, new.content, new.create_time);
        END
    ''')
    
    # Conversations trigger
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS conversations_fts_insert AFTER INSERT ON conversations BEGIN
            INSERT INTO conversations_fts(conversation_id, title, create_time)
            VALUES (new.conversation_id, COALESCE(new.title, ''), new.create_time);
        END
    ''')
    
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS conversations_fts_delete AFTER DELETE ON conversations BEGIN
            DELETE FROM conversations_fts WHERE conversation_id = old.conversation_id;
        END
    ''')
    
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS conversations_fts_update AFTER UPDATE ON conversations BEGIN
            DELETE FROM conversations_fts WHERE conversation_id = old.conversation_id;
            INSERT INTO conversations_fts(conversation_id, title, create_time)
            VALUES (new.conversation_id, COALESCE(new.title, ''), new.create_time);
        END
    ''')
    
    conn.commit()
    conn.close()
    print(f"FTS5 tables created successfully in {db_path}")


if __name__ == '__main__':
    create_fts5_tables()

