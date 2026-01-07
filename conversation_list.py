"""
Conversation list with sorting and filtering.

Features:
- Sort by: newest, oldest, longest, most messages
- Filter by date range
- Filter by tags, folders, starred
- Filter by AI source
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


DB_PATH = 'conversations.db'


def list_conversations(
    db_path: str = DB_PATH,
    sort_by: str = 'newest',
    limit: Optional[int] = None,
    offset: int = 0,
    date_from: Optional[float] = None,
    date_to: Optional[float] = None,
    tags: Optional[List[str]] = None,
    folder: Optional[str] = None,
    starred_only: bool = False,
    ai_source: Optional[str] = None,
    min_messages: Optional[int] = None,
    min_words: Optional[int] = None
) -> List[Dict]:
    """
    List conversations with sorting and filtering.
    
    Args:
        db_path: Database path
        sort_by: 'newest', 'oldest', 'longest', 'most_messages', 'most_words', 'longest_duration'
        limit: Maximum results
        offset: Offset for pagination
        date_from: Optional start timestamp
        date_to: Optional end timestamp
        tags: Optional list of tag names
        folder: Optional folder name
        starred_only: Only starred conversations
        ai_source: Filter by 'gpt' or 'claude'
        min_messages: Minimum message count
        min_words: Minimum word count
    
    Returns:
        List of conversations with metadata
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Build query
    joins = ["FROM conversations c"]
    where_parts = []
    params = []
    
    # Join stats table if needed for sorting/filtering
    needs_stats = sort_by in ['longest', 'most_messages', 'most_words', 'longest_duration'] or min_messages or min_words
    if needs_stats:
        joins.append("LEFT JOIN conversation_stats s ON s.conversation_id = c.conversation_id")
    else:
        # Still join for optional display, but don't require it
        joins.append("LEFT JOIN conversation_stats s ON s.conversation_id = c.conversation_id")
    
    # Join tags if filtering by tags
    if tags:
        joins.append("JOIN conversation_tags ct ON ct.conversation_id = c.conversation_id")
        joins.append("JOIN tags t ON t.tag_id = ct.tag_id")
        where_parts.append("t.name IN ({})".format(','.join(['?'] * len(tags))))
        params.extend(tags)
    
    # Join folders if filtering by folder
    if folder:
        joins.append("JOIN conversation_folders cf ON cf.conversation_id = c.conversation_id")
        joins.append("JOIN folders f ON f.folder_id = cf.folder_id")
        where_parts.append("f.name = ?")
        params.append(folder)
    
    # Date filters
    if date_from:
        where_parts.append("c.create_time >= ?")
        params.append(date_from)
    
    if date_to:
        where_parts.append("c.create_time <= ?")
        params.append(date_to)
    
    # Starred filter
    if starred_only:
        where_parts.append("c.is_starred = 1")
    
    # AI source filter
    if ai_source:
        where_parts.append("c.ai_source = ?")
        params.append(ai_source)
    
    # Message count filter
    if min_messages:
        where_parts.append("s.message_count_total >= ?")
        params.append(min_messages)
    
    # Word count filter
    if min_words:
        where_parts.append("s.word_count_total >= ?")
        params.append(min_words)
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    # Sorting
    order_by_map = {
        'newest': 'c.create_time DESC',
        'oldest': 'c.create_time ASC',
        'longest': 's.duration_seconds DESC NULLS LAST',
        'most_messages': 's.message_count_total DESC NULLS LAST',
        'most_words': 's.word_count_total DESC NULLS LAST',
        'longest_duration': 's.duration_seconds DESC NULLS LAST',
        'updated': 'c.update_time DESC NULLS LAST',
        'title': 'c.title ASC'
    }
    
    order_by = order_by_map.get(sort_by, order_by_map['newest'])
    
    # Build final query
    query = f'''
        SELECT DISTINCT
            c.conversation_id,
            c.title,
            c.create_time,
            c.update_time,
            c.is_starred,
            c.is_archived,
            c.ai_source,
            COALESCE(s.message_count_total, 0) as message_count_total,
            COALESCE(s.word_count_total, 0) as word_count_total,
            s.duration_seconds,
            COALESCE(s.active_days, 0) as active_days
        {' '.join(joins)}
        WHERE {where_clause}
        ORDER BY {order_by}
    '''
    
    if limit:
        query += f" LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    results = []
    
    for row in cursor:
        results.append({
            'conversation_id': row['conversation_id'],
            'title': row['title'],
            'create_time': row['create_time'],
            'update_time': row['update_time'],
            'is_starred': bool(row['is_starred']),
            'is_archived': bool(row['is_archived']),
            'ai_source': row['ai_source'],
            'message_count': row['message_count_total'] or 0,
            'word_count': row['word_count_total'] or 0,
            'duration_seconds': row['duration_seconds'],
            'active_days': row['active_days'] or 0
        })
    
    conn.close()
    return results


def get_conversation_tags(db_path: str, conversation_id: str) -> List[str]:
    """Get tags for a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT t.name
        FROM tags t
        JOIN conversation_tags ct ON ct.tag_id = t.tag_id
        WHERE ct.conversation_id = ?
        ORDER BY t.name
    ''', (conversation_id,))
    
    tags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tags


def get_conversation_folder(db_path: str, conversation_id: str) -> Optional[str]:
    """Get folder for a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT f.name
        FROM folders f
        JOIN conversation_folders cf ON cf.folder_id = f.folder_id
        WHERE cf.conversation_id = ?
        LIMIT 1
    ''', (conversation_id,))
    
    row = cursor.fetchone()
    folder = row[0] if row else None
    conn.close()
    return folder


if __name__ == '__main__':
    import sys
    
    sort_by = sys.argv[1] if len(sys.argv) > 1 else 'newest'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"Listing conversations (sort: {sort_by}, limit: {limit})")
    print("-"*70)
    
    results = list_conversations(sort_by=sort_by, limit=limit)
    
    print(f"Found {len(results)} conversations:\n")
    for i, conv in enumerate(results, 1):
        print(f"[{i}] {conv['title'] or '(no title)'}")
        print(f"     ID: {conv['conversation_id'][:40]}...")
        print(f"     Messages: {conv['message_count']}, Words: {conv['word_count']}")
        if conv['duration_seconds']:
            print(f"     Duration: {conv['duration_seconds']:.0f}s, Active days: {conv['active_days']}")
        print(f"     Source: {conv['ai_source']}, Starred: {conv['is_starred']}")
        print()

