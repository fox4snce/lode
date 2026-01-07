"""
Full-text search using SQLite FTS5.

Features:
- Phrase search
- AND/OR operators
- Exclude words (NOT)
- Prefix search
- Search within conversation
- Date filtering
- Jump-to-context (show N messages before/after)
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


DB_PATH = 'conversations.db'


def escape_fts_query(query: str) -> str:
    """Escape special FTS5 characters in query string."""
    # FTS5 special characters: ", ', \
    # We need to escape them for literal search
    return query.replace('"', '""').replace("'", "''")


def search_messages(
    query: str,
    db_path: str = DB_PATH,
    conversation_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    date_from: Optional[float] = None,
    date_to: Optional[float] = None
) -> List[Dict]:
    """
    Search messages using FTS5.
    
    Args:
        query: Search query (supports FTS5 syntax: AND, OR, NOT, prefix*)
        db_path: Database path
        conversation_id: Optional conversation ID to filter
        limit: Maximum results
        offset: Offset for pagination
        date_from: Optional start timestamp
        date_to: Optional end timestamp
    
    Returns:
        List of matching messages with context
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Build WHERE clause
    where_parts = []
    params = []
    
    # FTS5 search
    escaped_query = escape_fts_query(query)
    where_parts.append("messages_fts MATCH ?")
    params.append(escaped_query)
    
    # Conversation filter
    if conversation_id:
        where_parts.append("messages_fts.conversation_id = ?")
        params.append(conversation_id)
    
    # Date filters
    if date_from:
        where_parts.append("messages_fts.create_time >= ?")
        params.append(date_from)
    
    if date_to:
        where_parts.append("messages_fts.create_time <= ?")
        params.append(date_to)
    
    where_clause = " AND ".join(where_parts)
    
    # Query with ranking
    sql = f'''
        SELECT 
            m.conversation_id,
            m.message_id,
            m.role,
            m.content,
            m.create_time,
            c.title as conversation_title,
            rank
        FROM messages_fts
        JOIN messages m ON m.message_id = messages_fts.message_id 
            AND m.conversation_id = messages_fts.conversation_id
        JOIN conversations c ON c.conversation_id = m.conversation_id
        WHERE {where_clause}
        ORDER BY rank
        LIMIT ? OFFSET ?
    '''
    
    params.extend([limit, offset])
    
    cursor = conn.execute(sql, params)
    results = []
    
    for row in cursor:
        results.append({
            'conversation_id': row['conversation_id'],
            'message_id': row['message_id'],
            'role': row['role'],
            'content': row['content'],
            'create_time': row['create_time'],
            'conversation_title': row['conversation_title'],
            'rank': row['rank']
        })
    
    conn.close()
    return results


def search_conversations(
    query: str,
    db_path: str = DB_PATH,
    limit: int = 20,
    offset: int = 0,
    date_from: Optional[float] = None,
    date_to: Optional[float] = None
) -> List[Dict]:
    """
    Search conversation titles using FTS5.
    
    Args:
        query: Search query
        db_path: Database path
        limit: Maximum results
        offset: Offset for pagination
        date_from: Optional start timestamp
        date_to: Optional end timestamp
    
    Returns:
        List of matching conversations
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Build WHERE clause
    where_parts = []
    params = []
    
    # FTS5 search
    escaped_query = escape_fts_query(query)
    where_parts.append("conversations_fts MATCH ?")
    params.append(escaped_query)
    
    # Date filters
    if date_from:
        where_parts.append("conversations_fts.create_time >= ?")
        params.append(date_from)
    
    if date_to:
        where_parts.append("conversations_fts.create_time <= ?")
        params.append(date_to)
    
    where_clause = " AND ".join(where_parts)
    
    # Query
    sql = f'''
        SELECT 
            c.conversation_id,
            c.title,
            c.create_time,
            c.update_time,
            c.ai_source,
            rank
        FROM conversations_fts
        JOIN conversations c ON c.conversation_id = conversations_fts.conversation_id
        WHERE {where_clause}
        ORDER BY rank
        LIMIT ? OFFSET ?
    '''
    
    params.extend([limit, offset])
    
    cursor = conn.execute(sql, params)
    results = []
    
    for row in cursor:
        results.append({
            'conversation_id': row['conversation_id'],
            'title': row['title'],
            'create_time': row['create_time'],
            'update_time': row['update_time'],
            'ai_source': row['ai_source'],
            'rank': row['rank']
        })
    
    conn.close()
    return results


def get_message_context(
    db_path: str,
    conversation_id: str,
    message_id: str,
    context_before: int = 3,
    context_after: int = 3
) -> Dict:
    """
    Get message with context (N messages before/after).
    
    Args:
        db_path: Database path
        conversation_id: Conversation ID
        message_id: Message ID
        context_before: Number of messages before
        context_after: Number of messages after
    
    Returns:
        Dict with target message and context
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get target message
    cursor = conn.execute('''
        SELECT message_id, role, content, create_time
        FROM messages
        WHERE conversation_id = ? AND message_id = ?
    ''', (conversation_id, message_id))
    
    target = cursor.fetchone()
    if not target:
        conn.close()
        return {'target': None, 'before': [], 'after': []}
    
    target_time = target['create_time']
    
    # Get messages before
    cursor = conn.execute('''
        SELECT message_id, role, content, create_time
        FROM messages
        WHERE conversation_id = ? AND create_time < ?
        ORDER BY create_time DESC
        LIMIT ?
    ''', (conversation_id, target_time, context_before))
    
    before = [dict(row) for row in cursor.fetchall()]
    before.reverse()  # Chronological order
    
    # Get messages after
    cursor = conn.execute('''
        SELECT message_id, role, content, create_time
        FROM messages
        WHERE conversation_id = ? AND create_time > ?
        ORDER BY create_time ASC
        LIMIT ?
    ''', (conversation_id, target_time, context_after))
    
    after = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'target': dict(target),
        'before': before,
        'after': after
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python search_fts5.py <query> [--conversation-id ID] [--limit N]")
        sys.exit(1)
    
    query = sys.argv[1]
    conversation_id = None
    limit = 20
    
    # Parse args
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--conversation-id' and i + 1 < len(sys.argv):
            conversation_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    print(f"Searching for: '{query}'")
    if conversation_id:
        print(f"  In conversation: {conversation_id}")
    print("-"*70)
    
    if conversation_id:
        results = search_messages(query, conversation_id=conversation_id, limit=limit)
        print(f"Found {len(results)} messages:\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r['conversation_title']} - {r['role']}")
            print(f"    {r['content'][:100]}...")
            print()
    else:
        # Search both
        conv_results = search_conversations(query, limit=limit)
        msg_results = search_messages(query, limit=limit)
        
        print(f"Conversations: {len(conv_results)}")
        for r in conv_results:
            print(f"  - {r['title']} ({r['conversation_id'][:40]}...)")
        
        print(f"\nMessages: {len(msg_results)}")
        for r in msg_results[:5]:  # Show first 5
            print(f"  - {r['conversation_title']} - {r['role']}: {r['content'][:80]}...")

