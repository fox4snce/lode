"""
Conversation API routes.
"""
from fastapi import APIRouter, Query, Path as PathParam, HTTPException
from typing import List, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models import ConversationSummary, ConversationDetail
from backend.db import get_db_connection, check_database_initialized
import sqlite3

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

from backend.db import get_db_connection as get_db


@router.get("/", response_model=List[ConversationSummary])
async def list_conversations(
    sort: str = Query("newest", description="Sort order: newest, oldest, longest, most_messages, most_words"),
    q: Optional[str] = Query(None, description="Search query"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    date_from: Optional[str] = Query(None, description="Date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date to (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List conversations with filtering and sorting.
    
    Returns a list of conversation summaries.
    """
    # TODO: Implement actual filtering/sorting using existing backend functions
    # For now, return mock data
    
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    # Build query
    query = """
        SELECT 
            c.conversation_id,
            c.title,
            c.create_time,
            c.update_time,
            c.ai_source,
            c.is_starred,
            COALESCE(s.message_count_total, 0) as message_count,
            COALESCE(s.word_count_total, 0) as word_count,
            ct.custom_title
        FROM conversations c
        LEFT JOIN conversation_stats s ON s.conversation_id = c.conversation_id
        LEFT JOIN custom_titles ct ON ct.conversation_id = c.conversation_id
        WHERE 1=1
    """
    params = []
    
    # Apply filters
    if tag:
        query += """
            AND c.conversation_id IN (
                SELECT ct.conversation_id 
                FROM conversation_tags ct
                JOIN tags t ON t.tag_id = ct.tag_id
                WHERE t.name = ?
            )
        """
        params.append(tag)
    
    if date_from:
        query += " AND c.create_time >= ?"
        params.append(date_from)
    
    if date_to:
        query += " AND c.create_time <= ?"
        params.append(date_to)
    
    # Apply sorting
    if sort == "newest":
        query += " ORDER BY c.create_time DESC NULLS LAST"
    elif sort == "oldest":
        query += " ORDER BY c.create_time ASC NULLS LAST"
    elif sort == "longest":
        query += " ORDER BY s.word_count_total DESC NULLS LAST"
    elif sort == "most_messages":
        query += " ORDER BY s.message_count_total DESC NULLS LAST"
    elif sort == "most_words":
        query += " ORDER BY s.word_count_total DESC NULLS LAST"
    else:
        query += " ORDER BY c.create_time DESC NULLS LAST"
    
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    # Get tags for each conversation
    results = []
    for row in rows:
        conv_id = row['conversation_id']
        
        # Get tags
        tag_cursor = conn.execute("""
            SELECT t.name
            FROM tags t
            JOIN conversation_tags ct ON ct.tag_id = t.tag_id
            WHERE ct.conversation_id = ?
        """, (conv_id,))
        tags = [r[0] for r in tag_cursor.fetchall()]
        
        results.append(ConversationSummary(
            conversation_id=conv_id,
            title=row['title'],
            create_time=row['create_time'],
            update_time=row['update_time'],
            message_count=row['message_count'] or 0,
            word_count=row['word_count'] or 0,
            ai_source=row['ai_source'],
            is_starred=bool(row['is_starred']),
            tags=tags,
            custom_title=row['custom_title']
        ))
    
    conn.close()
    return results


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str = PathParam(..., description="Conversation ID")):
    """Get full conversation details."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("""
        SELECT 
            c.conversation_id,
            c.title,
            c.create_time,
            c.update_time,
            c.ai_source,
            c.is_starred,
            ct.custom_title
        FROM conversations c
        LEFT JOIN custom_titles ct ON ct.conversation_id = c.conversation_id
        WHERE c.conversation_id = ?
    """, (conversation_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get tags
    tag_cursor = conn.execute("""
        SELECT t.name
        FROM tags t
        JOIN conversation_tags ct ON ct.tag_id = t.tag_id
        WHERE ct.conversation_id = ?
    """, (conversation_id,))
    tags = [r[0] for r in tag_cursor.fetchall()]
    
    # Get stats
    stats_cursor = conn.execute("""
        SELECT * FROM conversation_stats
        WHERE conversation_id = ?
    """, (conversation_id,))
    stats_row = stats_cursor.fetchone()
    stats = dict(stats_row) if stats_row else None
    
    conn.close()
    
    return ConversationDetail(
        conversation_id=row['conversation_id'],
        title=row['title'],
        custom_title=row['custom_title'],
        create_time=row['create_time'],
        update_time=row['update_time'],
        ai_source=row['ai_source'],
        is_starred=bool(row['is_starred']),
        tags=tags,
        stats=stats
    )

