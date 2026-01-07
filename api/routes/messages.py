"""
Message API routes.
"""
from fastapi import APIRouter, Path as PathParam, Query, HTTPException
from typing import List, Optional
import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models import Message
from backend.db import get_db_connection as get_db

router = APIRouter(prefix="/api/conversations", tags=["messages"])


@router.get("/{conversation_id}/messages", response_model=List[Message])
async def get_messages(
    conversation_id: str = PathParam(..., description="Conversation ID"),
    around_message_id: Optional[str] = Query(None, description="Get messages around this message"),
    context_n: int = Query(5, ge=1, le=50, description="Number of messages before/after")
):
    """
    Get messages for a conversation.
    
    If around_message_id is provided, returns that message plus context_n messages
    before and after. Otherwise, returns all messages.
    """
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    # Verify conversation exists
    cursor = conn.execute("SELECT conversation_id FROM conversations WHERE conversation_id = ?", (conversation_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if around_message_id:
        # Get the target message's position
        cursor = conn.execute("""
            SELECT id, create_time
            FROM messages
            WHERE conversation_id = ? AND message_id = ?
        """, (conversation_id, around_message_id))
        
        target = cursor.fetchone()
        if not target:
            conn.close()
            raise HTTPException(status_code=404, detail="Message not found")
        
        target_id = target['id']
        target_time = target['create_time']
        
        # Get messages around it
        cursor = conn.execute("""
            SELECT message_id, role, content, create_time, parent_id
            FROM messages
            WHERE conversation_id = ?
                AND (
                    (create_time = ? AND id <= ?)
                    OR (create_time < ?)
                    OR (create_time > ?)
                )
            ORDER BY create_time ASC, id ASC
            LIMIT ?
        """, (conversation_id, target_time, target_id, target_time, target_time, context_n * 2 + 1))
    else:
        # Get all messages
        cursor = conn.execute("""
            SELECT message_id, role, content, create_time, parent_id
            FROM messages
            WHERE conversation_id = ?
            ORDER BY create_time ASC, id ASC
        """, (conversation_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        Message(
            message_id=row['message_id'],
            role=row['role'],
            content=row['content'] or '',
            create_time=row['create_time'],
            parent_id=row['parent_id']
        )
        for row in rows
    ]

