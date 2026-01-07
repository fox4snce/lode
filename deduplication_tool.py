"""
Deduplication tool for finding and managing duplicate messages/conversations.
"""
import sqlite3
import hashlib
import re
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


DB_PATH = 'conversations.db'


def normalize_content(content: str) -> str:
    """
    Normalize content for hashing.
    
    - Lowercase
    - Strip whitespace
    - Normalize multiple spaces to single space
    - Remove leading/trailing whitespace
    """
    if not content:
        return ""
    
    # Lowercase
    normalized = content.lower()
    
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Strip
    normalized = normalized.strip()
    
    return normalized


def hash_content(content: str) -> str:
    """Hash normalized content using SHA256."""
    normalized = normalize_content(content)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def hash_all_messages(db_path: str, conversation_id: Optional[str] = None):
    """Hash all messages and store in message_hashes table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get messages
    if conversation_id:
        cursor.execute('''
            SELECT conversation_id, message_id, content
            FROM messages
            WHERE conversation_id = ? AND content IS NOT NULL
        ''', (conversation_id,))
    else:
        cursor.execute('''
            SELECT conversation_id, message_id, content
            FROM messages
            WHERE content IS NOT NULL
        ''')
    
    messages = cursor.fetchall()
    
    # Hash and store
    for conv_id, msg_id, content in messages:
        content_hash = hash_content(content)
        
        # Check if already exists
        cursor.execute('''
            SELECT id FROM message_hashes
            WHERE conversation_id = ? AND message_id = ?
        ''', (conv_id, msg_id))
        
        if cursor.fetchone():
            # Update existing
            cursor.execute('''
                UPDATE message_hashes
                SET content_hash = ?
                WHERE conversation_id = ? AND message_id = ?
            ''', (content_hash, conv_id, msg_id))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO message_hashes 
                (conversation_id, message_id, content_hash)
                VALUES (?, ?, ?)
            ''', (conv_id, msg_id, content_hash))
    
    conn.commit()
    conn.close()


def find_duplicate_messages(
    db_path: str,
    conversation_id: Optional[str] = None
) -> List[Dict]:
    """
    Find duplicate messages by content hash.
    
    Returns:
        List of dicts with duplicate groups
    """
    # First ensure all messages are hashed
    hash_all_messages(db_path, conversation_id)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Find messages with same hash
    if conversation_id:
        cursor = conn.execute('''
            SELECT 
                mh.content_hash,
                mh.conversation_id,
                mh.message_id,
                m.content,
                m.role
            FROM message_hashes mh
            JOIN messages m ON m.conversation_id = mh.conversation_id 
                AND m.message_id = mh.message_id
            WHERE mh.conversation_id = ?
                AND mh.content_hash IN (
                    SELECT content_hash
                    FROM message_hashes
                    WHERE conversation_id = ?
                    GROUP BY content_hash
                    HAVING COUNT(*) > 1
                )
            ORDER BY mh.content_hash, mh.conversation_id, mh.message_id
        ''', (conversation_id, conversation_id))
    else:
        cursor = conn.execute('''
            SELECT 
                mh.content_hash,
                mh.conversation_id,
                mh.message_id,
                m.content,
                m.role
            FROM message_hashes mh
            JOIN messages m ON m.conversation_id = mh.conversation_id 
                AND m.message_id = mh.message_id
            WHERE mh.content_hash IN (
                SELECT content_hash
                FROM message_hashes
                GROUP BY content_hash
                HAVING COUNT(*) > 1
            )
            ORDER BY mh.content_hash, mh.conversation_id, mh.message_id
        ''')
    
    # Group by hash
    hash_groups = defaultdict(list)
    for row in cursor.fetchall():
        hash_groups[row['content_hash']].append(dict(row))
    
    # Convert to list of groups
    duplicate_groups = []
    for content_hash, messages in hash_groups.items():
        if len(messages) > 1:
            duplicate_groups.append({
                'content_hash': content_hash,
                'count': len(messages),
                'messages': messages
            })
    
    conn.close()
    return duplicate_groups


def mark_duplicate_messages(
    db_path: str,
    duplicate_groups: List[Dict],
    keep_first: bool = True
):
    """
    Mark duplicate messages, keeping the first occurrence as original.
    
    Args:
        db_path: Database path
        duplicate_groups: List of duplicate groups from find_duplicate_messages
        keep_first: If True, keep first message in each group as original
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for group in duplicate_groups:
        messages = group['messages']
        
        if keep_first:
            # First message is original
            original = messages[0]
            duplicates = messages[1:]
        else:
            # Last message is original (newest)
            original = messages[-1]
            duplicates = messages[:-1]
        
        # Mark original
        cursor.execute('''
            UPDATE message_hashes
            SET is_duplicate = 0, original_message_id = NULL
            WHERE conversation_id = ? AND message_id = ?
        ''', (original['conversation_id'], original['message_id']))
        
        # Mark duplicates
        for dup in duplicates:
            cursor.execute('''
                UPDATE message_hashes
                SET is_duplicate = 1, 
                    original_message_id = ?
                WHERE conversation_id = ? AND message_id = ?
            ''', (
                original['message_id'],
                dup['conversation_id'],
                dup['message_id']
            ))
    
    conn.commit()
    conn.close()


def hash_conversation_content(db_path: str, conversation_id: str) -> str:
    """Hash all message content in a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT content
        FROM messages
        WHERE conversation_id = ? AND content IS NOT NULL
        ORDER BY create_time ASC, id ASC
    ''', (conversation_id,))
    
    # Concatenate all content
    all_content = ' '.join(row[0] for row in cursor.fetchall())
    conn.close()
    
    return hash_content(all_content)


def hash_all_conversations(db_path: str):
    """Hash all conversations and store in conversation_hashes table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all conversations
    cursor.execute('SELECT conversation_id FROM conversations')
    conversations = cursor.fetchall()
    
    for (conv_id,) in conversations:
        content_hash = hash_conversation_content(db_path, conv_id)
        
        # Check if exists
        cursor.execute('''
            SELECT id FROM conversation_hashes WHERE conversation_id = ?
        ''', (conv_id,))
        
        if cursor.fetchone():
            cursor.execute('''
                UPDATE conversation_hashes
                SET content_hash = ?
                WHERE conversation_id = ?
            ''', (content_hash, conv_id))
        else:
            cursor.execute('''
                INSERT INTO conversation_hashes 
                (conversation_id, content_hash)
                VALUES (?, ?)
            ''', (conv_id, content_hash))
    
    conn.commit()
    conn.close()


def find_duplicate_conversations(db_path: str) -> List[Dict]:
    """Find duplicate conversations by content hash."""
    # Ensure all conversations are hashed
    hash_all_conversations(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Find conversations with same hash
    cursor = conn.execute('''
        SELECT 
            ch.content_hash,
            ch.conversation_id,
            c.title,
            COUNT(*) as count
        FROM conversation_hashes ch
        JOIN conversations c ON c.conversation_id = ch.conversation_id
        GROUP BY ch.content_hash
        HAVING COUNT(*) > 1
        ORDER BY ch.content_hash
    ''')
    
    # Group by hash
    hash_groups = defaultdict(list)
    for row in cursor.fetchall():
        hash_groups[row['content_hash']].append(dict(row))
    
    # Convert to list
    duplicate_groups = []
    for content_hash, conversations in hash_groups.items():
        if len(conversations) > 1:
            duplicate_groups.append({
                'content_hash': content_hash,
                'count': len(conversations),
                'conversations': conversations
            })
    
    conn.close()
    return duplicate_groups


def get_deduplication_stats(db_path: str) -> Dict:
    """Get statistics about duplicates."""
    conn = sqlite3.connect(db_path)
    
    # Message duplicates
    cursor = conn.execute('''
        SELECT COUNT(*) FROM message_hashes WHERE is_duplicate = 1
    ''')
    duplicate_messages = cursor.fetchone()[0]
    
    cursor = conn.execute('SELECT COUNT(*) FROM message_hashes')
    total_hashed_messages = cursor.fetchone()[0]
    
    # Conversation duplicates
    cursor = conn.execute('''
        SELECT COUNT(*) FROM conversation_hashes WHERE is_duplicate = 1
    ''')
    duplicate_conversations = cursor.fetchone()[0]
    
    cursor = conn.execute('SELECT COUNT(*) FROM conversation_hashes')
    total_hashed_conversations = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'duplicate_messages': duplicate_messages,
        'total_hashed_messages': total_hashed_messages,
        'duplicate_conversations': duplicate_conversations,
        'total_hashed_conversations': total_hashed_conversations
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python deduplication_tool.py <command> [args...]")
        print("\nCommands:")
        print("  hash-messages [conversation_id]")
        print("  find-messages [conversation_id]")
        print("  mark-messages [conversation_id]")
        print("  hash-conversations")
        print("  find-conversations")
        print("  stats")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'hash-messages':
            conv_id = args[0] if args else None
            hash_all_messages(DB_PATH, conv_id)
            print(f"Hashed messages{' for ' + conv_id if conv_id else ''}")
        
        elif command == 'find-messages':
            conv_id = args[0] if args else None
            duplicates = find_duplicate_messages(DB_PATH, conv_id)
            print(f"Found {len(duplicates)} duplicate message groups:")
            for group in duplicates:
                print(f"  Hash {group['content_hash'][:8]}...: {group['count']} duplicates")
                for msg in group['messages'][:3]:  # Show first 3
                    print(f"    - {msg['conversation_id']}/{msg['message_id']}")
        
        elif command == 'mark-messages':
            conv_id = args[0] if args else None
            duplicates = find_duplicate_messages(DB_PATH, conv_id)
            mark_duplicate_messages(DB_PATH, duplicates)
            print(f"Marked {len(duplicates)} duplicate groups")
        
        elif command == 'hash-conversations':
            hash_all_conversations(DB_PATH)
            print("Hashed all conversations")
        
        elif command == 'find-conversations':
            duplicates = find_duplicate_conversations(DB_PATH)
            print(f"Found {len(duplicates)} duplicate conversation groups:")
            for group in duplicates:
                print(f"  Hash {group['content_hash'][:8]}...: {group['count']} duplicates")
                for conv in group['conversations']:
                    print(f"    - {conv['conversation_id']}: {conv['title']}")
        
        elif command == 'stats':
            stats = get_deduplication_stats(DB_PATH)
            print("Deduplication Statistics:")
            print(f"  Duplicate messages: {stats['duplicate_messages']}/{stats['total_hashed_messages']}")
            print(f"  Duplicate conversations: {stats['duplicate_conversations']}/{stats['total_hashed_conversations']}")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

