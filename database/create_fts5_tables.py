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
    
    # Ensure triggers are correct (drop/recreate) and rebuild indexes.
    #
    # IMPORTANT: These are external-content FTS5 tables (content='messages'/'conversations').
    # The correct maintenance pattern uses special "delete" inserts, NOT `DELETE FROM messages_fts`,
    # otherwise the index can accumulate orphan rowids and produce false positives.
    print("Populating FTS5 tables with existing data...")
    
    # Drop old triggers (they may exist with incorrect definitions)
    cursor.execute("DROP TRIGGER IF EXISTS messages_fts_insert")
    cursor.execute("DROP TRIGGER IF EXISTS messages_fts_delete")
    cursor.execute("DROP TRIGGER IF EXISTS messages_fts_update")
    cursor.execute("DROP TRIGGER IF EXISTS conversations_fts_insert")
    cursor.execute("DROP TRIGGER IF EXISTS conversations_fts_delete")
    cursor.execute("DROP TRIGGER IF EXISTS conversations_fts_update")

    # Create triggers to keep FTS5 in sync with main tables (external-content safe)
    cursor.execute('''
        CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(rowid, conversation_id, message_id, role, content, create_time)
            VALUES (new.id, new.conversation_id, new.message_id, new.role, new.content, new.create_time);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER messages_fts_delete AFTER DELETE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, conversation_id, message_id, role, content, create_time)
            VALUES ('delete', old.id, old.conversation_id, old.message_id, old.role, old.content, old.create_time);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER messages_fts_update AFTER UPDATE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, conversation_id, message_id, role, content, create_time)
            VALUES ('delete', old.id, old.conversation_id, old.message_id, old.role, old.content, old.create_time);
            INSERT INTO messages_fts(rowid, conversation_id, message_id, role, content, create_time)
            VALUES (new.id, new.conversation_id, new.message_id, new.role, new.content, new.create_time);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER conversations_fts_insert AFTER INSERT ON conversations BEGIN
            INSERT INTO conversations_fts(rowid, conversation_id, title, create_time)
            VALUES (new.id, new.conversation_id, COALESCE(new.title, ''), new.create_time);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER conversations_fts_delete AFTER DELETE ON conversations BEGIN
            INSERT INTO conversations_fts(conversations_fts, rowid, conversation_id, title, create_time)
            VALUES ('delete', old.id, old.conversation_id, COALESCE(old.title, ''), old.create_time);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER conversations_fts_update AFTER UPDATE ON conversations BEGIN
            INSERT INTO conversations_fts(conversations_fts, rowid, conversation_id, title, create_time)
            VALUES ('delete', old.id, old.conversation_id, COALESCE(old.title, ''), old.create_time);
            INSERT INTO conversations_fts(rowid, conversation_id, title, create_time)
            VALUES (new.id, new.conversation_id, COALESCE(new.title, ''), new.create_time);
        END
    ''')

    # Rebuild indexes from their external content tables (clears orphan rowids / stale tokens)
    cursor.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    cursor.execute("INSERT INTO conversations_fts(conversations_fts) VALUES('rebuild')")
    
    conn.commit()
    conn.close()
    print(f"FTS5 tables created successfully in {db_path}")


if __name__ == '__main__':
    create_fts5_tables()

