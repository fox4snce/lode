"""
Import Lode conversation exports from JSON.

Handles the Lode export format with lode_export_format_version identifier.
Supports single-conversation JSON files (one per file).
"""
import json
import sqlite3
from pathlib import Path
from typing import Tuple


def is_lode_export(file_path: str) -> bool:
    """
    Check if a file appears to be a Lode export by peeking at the start.
    Distinguishes from OpenAI, Claude, or other JSON files.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            chunk = f.read(512)
        return '"lode_export_format_version"' in chunk
    except (OSError, UnicodeDecodeError):
        return False


def import_lode_conversations(file_path: str, db_path: str) -> Tuple[int, int]:
    """
    Import a single Lode JSON export file into the database.

    Args:
        file_path: Path to the .json file
        db_path: Path to conversations.db

    Returns:
        Tuple of (conversations_imported, messages_imported)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'lode_export_format_version' not in data:
        raise ValueError(
            "Not a Lode export: missing 'lode_export_format_version'. "
            "Expected format v1.0 with that identifier."
        )

    conv = data.get('conversation')
    messages = data.get('messages', [])

    if not conv or not isinstance(conv, dict):
        raise ValueError("Lode export missing or invalid 'conversation' object")

    conversation_id = conv.get('conversation_id')
    if not conversation_id:
        raise ValueError("Lode export missing 'conversation_id'")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Duplicate detection
    cursor.execute('SELECT conversation_id FROM conversations WHERE conversation_id = ?', (conversation_id,))
    if cursor.fetchone():
        conn.close()
        return (0, 0)

    # Insert conversation
    cursor.execute('''
        INSERT OR REPLACE INTO conversations
        (conversation_id, title, create_time, update_time, is_archived, is_starred,
         default_model_slug, conversation_origin, ai_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        conversation_id,
        conv.get('title'),
        conv.get('create_time'),
        conv.get('update_time'),
        int(conv.get('is_archived', 0) or 0),
        int(conv.get('is_starred', 0) or 0),
        conv.get('default_model_slug') or 'lode',
        conv.get('conversation_origin') or 'lode',
        conv.get('ai_source') or 'lode',
    ))

    # Delete existing messages (re-import case)
    cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))

    # Insert messages
    msg_count = 0
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        msg_id = msg.get('message_id')
        if not msg_id:
            continue
        cursor.execute('''
            INSERT OR REPLACE INTO messages
            (conversation_id, message_id, parent_id, role, content, create_time, weight, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conversation_id,
            msg_id,
            msg.get('parent_id'),
            msg.get('role') or 'user',
            msg.get('content') or '',
            msg.get('create_time'),
            msg.get('weight', 1.0),
            msg.get('status', 'finished_successfully'),
        ))
        msg_count += 1

    conn.commit()
    conn.close()
    return (1, msg_count)


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python import_lode_conversations.py <path_to_lode_export.json> [db_path]")
        sys.exit(1)
    db_path = sys.argv[2] if len(sys.argv) > 2 else 'conversations.db'
    convs, msgs = import_lode_conversations(path, db_path)
    print(f"Imported {convs} conversation(s), {msgs} message(s)")
