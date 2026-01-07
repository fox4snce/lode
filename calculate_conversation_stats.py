"""
Calculate and store conversation statistics.

Calculates:
- Message counts (total, user, assistant, system)
- Character/word counts per conversation and per speaker
- Conversation duration (first → last message)
- Active days (distinct days)
- Average/max message length
- URL, code block, file path counts
"""
import sqlite3
import re
from typing import Dict, Optional
from datetime import datetime


DB_PATH = 'conversations.db'

# Regex patterns for content analysis
URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```', re.MULTILINE)
FILE_PATH_PATTERN = re.compile(r'(?:[A-Z]:\\|/)(?:[^/\s<>:"|?*]+[/\\])*[^/\s<>:"|?*]+', re.IGNORECASE)


def count_urls(text: str) -> int:
    """Count URLs in text."""
    return len(URL_PATTERN.findall(text))


def count_code_blocks(text: str) -> int:
    """Count fenced code blocks in text."""
    return len(CODE_BLOCK_PATTERN.findall(text))


def count_file_paths(text: str) -> int:
    """Count file paths in text."""
    return len(FILE_PATH_PATTERN.findall(text))


def calculate_conversation_stats(conn: sqlite3.Connection, conversation_id: str) -> Optional[Dict]:
    """Calculate statistics for a single conversation."""
    
    # Get all messages for this conversation
    cursor = conn.execute('''
        SELECT role, content, create_time
        FROM messages
        WHERE conversation_id = ?
        ORDER BY create_time ASC
    ''', (conversation_id,))
    
    messages = cursor.fetchall()
    if not messages:
        return None
    
    # Initialize counters
    stats = {
        'message_count_total': len(messages),
        'message_count_user': 0,
        'message_count_assistant': 0,
        'message_count_system': 0,
        'character_count_total': 0,
        'word_count_total': 0,
        'character_count_user': 0,
        'word_count_user': 0,
        'character_count_assistant': 0,
        'word_count_assistant': 0,
        'character_count_system': 0,
        'word_count_system': 0,
        'url_count': 0,
        'code_block_count': 0,
        'file_path_count': 0,
        'message_lengths': [],
        'timestamps': []
    }
    
    # Process each message
    for role, content, create_time in messages:
        if not content:
            continue
        
        # Count by role
        if role == 'user':
            stats['message_count_user'] += 1
        elif role == 'assistant':
            stats['message_count_assistant'] += 1
        elif role == 'system':
            stats['message_count_system'] += 1
        
        # Character and word counts
        char_count = len(content)
        word_count = len(content.split())
        
        stats['character_count_total'] += char_count
        stats['word_count_total'] += word_count
        stats['message_lengths'].append(char_count)
        
        if role == 'user':
            stats['character_count_user'] += char_count
            stats['word_count_user'] += word_count
        elif role == 'assistant':
            stats['character_count_assistant'] += char_count
            stats['word_count_assistant'] += word_count
        elif role == 'system':
            stats['character_count_system'] += char_count
            stats['word_count_system'] += word_count
        
        # Content analysis
        stats['url_count'] += count_urls(content)
        stats['code_block_count'] += count_code_blocks(content)
        stats['file_path_count'] += count_file_paths(content)
        
        # Collect timestamps
        if create_time:
            stats['timestamps'].append(create_time)
    
    # Calculate derived stats
    if stats['message_lengths']:
        stats['avg_message_length'] = sum(stats['message_lengths']) / len(stats['message_lengths'])
        stats['max_message_length'] = max(stats['message_lengths'])
    else:
        stats['avg_message_length'] = 0.0
        stats['max_message_length'] = 0
    
    # Calculate duration and active days
    if stats['timestamps']:
        stats['first_message_time'] = min(stats['timestamps'])
        stats['last_message_time'] = max(stats['timestamps'])
        stats['duration_seconds'] = stats['last_message_time'] - stats['first_message_time']
        
        # Count distinct days
        days = set()
        for ts in stats['timestamps']:
            try:
                dt = datetime.fromtimestamp(ts)
                days.add(dt.date())
            except (ValueError, OSError):
                pass
        stats['active_days'] = len(days)
    else:
        stats['first_message_time'] = None
        stats['last_message_time'] = None
        stats['duration_seconds'] = None
        stats['active_days'] = 0
    
    # Get model/provider from conversation table
    cursor = conn.execute('''
        SELECT default_model_slug, ai_source
        FROM conversations
        WHERE conversation_id = ?
    ''', (conversation_id,))
    
    row = cursor.fetchone()
    if row:
        stats['model_name'] = row[0]
        stats['provider'] = row[1]
    
    # Remove temporary fields
    del stats['message_lengths']
    del stats['timestamps']
    
    return stats


def store_conversation_stats(conn: sqlite3.Connection, conversation_id: str, stats: Dict):
    """Store calculated statistics in the database."""
    
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO conversation_stats (
            conversation_id,
            message_count_total, message_count_user, message_count_assistant, message_count_system,
            character_count_total, word_count_total,
            character_count_user, word_count_user,
            character_count_assistant, word_count_assistant,
            character_count_system, word_count_system,
            first_message_time, last_message_time, duration_seconds, active_days,
            avg_message_length, max_message_length,
            url_count, code_block_count, file_path_count,
            model_name, provider
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        conversation_id,
        stats['message_count_total'],
        stats['message_count_user'],
        stats['message_count_assistant'],
        stats['message_count_system'],
        stats['character_count_total'],
        stats['word_count_total'],
        stats['character_count_user'],
        stats['word_count_user'],
        stats['character_count_assistant'],
        stats['word_count_assistant'],
        stats['character_count_system'],
        stats['word_count_system'],
        stats['first_message_time'],
        stats['last_message_time'],
        stats['duration_seconds'],
        stats['active_days'],
        stats['avg_message_length'],
        stats['max_message_length'],
        stats['url_count'],
        stats['code_block_count'],
        stats['file_path_count'],
        stats.get('model_name'),
        stats.get('provider')
    ))
    
    conn.commit()


def calculate_all_conversations(db_path: str = DB_PATH, limit: Optional[int] = None, force: bool = False):
    """Calculate statistics for all conversations."""
    
    conn = sqlite3.connect(db_path)
    
    # Get conversation IDs
    query = 'SELECT conversation_id FROM conversations ORDER BY create_time DESC'
    if limit:
        query += f' LIMIT {limit}'
    
    cursor = conn.execute(query)
    conversation_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"Calculating stats for {len(conversation_ids)} conversations...")
    print("-"*70)
    
    calculated = 0
    skipped = 0
    errors = 0
    
    for idx, conv_id in enumerate(conversation_ids, 1):
        # Check if already calculated (unless force)
        if not force:
            cursor = conn.execute('''
                SELECT 1 FROM conversation_stats WHERE conversation_id = ?
            ''', (conv_id,))
            if cursor.fetchone():
                skipped += 1
                continue
        
        try:
            stats = calculate_conversation_stats(conn, conv_id)
            if stats:
                store_conversation_stats(conn, conv_id, stats)
                calculated += 1
                print(f"[{idx}/{len(conversation_ids)}] {conv_id[:40]}... "
                      f"({stats['message_count_total']} msgs, {stats['word_count_total']} words)")
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            print(f"[{idx}/{len(conversation_ids)}] ERROR: {conv_id[:40]}... - {e}")
    
    print("\n" + "="*70)
    print(f"Complete: {calculated} calculated, {skipped} skipped, {errors} errors")
    print("="*70)
    
    conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate conversation statistics')
    parser.add_argument('--db', default=DB_PATH, help='Database path')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of conversations')
    parser.add_argument('--force', action='store_true', help='Recalculate even if already calculated')
    parser.add_argument('--conversation', help='Calculate stats for single conversation ID')
    
    args = parser.parse_args()
    
    if args.conversation:
        # Single conversation
        conn = sqlite3.connect(args.db)
        stats = calculate_conversation_stats(conn, args.conversation)
        if stats:
            store_conversation_stats(conn, args.conversation, stats)
            print(f"Stats calculated for {args.conversation}")
            print(f"  Messages: {stats['message_count_total']}")
            print(f"  Words: {stats['word_count_total']}")
            print(f"  Duration: {stats['duration_seconds']:.0f}s" if stats['duration_seconds'] else "  Duration: N/A")
            print(f"  Active days: {stats['active_days']}")
        else:
            print(f"No messages found for {args.conversation}")
        conn.close()
    else:
        # All conversations
        calculate_all_conversations(args.db, args.limit, args.force)

