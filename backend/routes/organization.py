"""
Organization API routes (tags, notes, bookmarks, etc.)
"""
from fastapi import APIRouter, Path as PathParam, HTTPException, Body, Request
from fastapi.responses import HTMLResponse, Response
from typing import List, Optional
from pydantic import BaseModel
from backend.db import get_db_connection, check_database_initialized

router = APIRouter(prefix="/api", tags=["organization"])


class TagRequest(BaseModel):
    name: str

class NoteRequest(BaseModel):
    note_text: str
    message_id: Optional[str] = None

class BookmarkRequest(BaseModel):
    message_id: Optional[str] = None
    note: Optional[str] = None


@router.get("/tags", response_model=List[dict])
async def list_tags():
    """List all tags."""
    if not check_database_initialized():
        return []
    
    import organization_api
    from backend.db import get_db_path
    tags = organization_api.list_tags(str(get_db_path()))
    return tags


@router.post("/conversations/{conversation_id}/tags")
async def add_tag(conversation_id: str = PathParam(...), request: TagRequest = Body(...)):
    """Add a tag to a conversation."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    import organization_api
    from backend.db import get_db_path
    
    if organization_api.add_tag_to_conversation(str(get_db_path()), conversation_id, request.name):
        return {"status": "added"}
    raise HTTPException(status_code=400, detail="Failed to add tag")


@router.delete("/conversations/{conversation_id}/tags/{tag_name}")
async def remove_tag(conversation_id: str = PathParam(...), tag_name: str = PathParam(...)):
    """Remove a tag from a conversation."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    import organization_api
    from backend.db import get_db_path
    
    if organization_api.remove_tag_from_conversation(str(get_db_path()), conversation_id, tag_name):
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Tag not found")


@router.get("/conversations/{conversation_id}/tags", response_model=List[str])
async def get_conversation_tags(conversation_id: str = PathParam(...)):
    """Get tags for a conversation."""
    if not check_database_initialized():
        return []
    
    import organization_api
    from backend.db import get_db_path
    return organization_api.get_conversation_tags(str(get_db_path()), conversation_id)


@router.get("/conversations/{conversation_id}/notes", response_model=List[dict])
async def list_notes(conversation_id: str = PathParam(...), message_id: Optional[str] = None):
    """List notes for a conversation."""
    if not check_database_initialized():
        return []
    
    import organization_api
    from backend.db import get_db_path
    return organization_api.list_notes(str(get_db_path()), conversation_id, message_id)


@router.post("/conversations/{conversation_id}/notes")
async def create_note(conversation_id: str = PathParam(...), request: NoteRequest = Body(...)):
    """Create a note."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    import organization_api
    from backend.db import get_db_path
    
    note_id = organization_api.create_note(str(get_db_path()), conversation_id, request.note_text, request.message_id)
    return {"note_id": note_id, "status": "created"}


@router.get("/conversations/{conversation_id}/bookmarks", response_model=List[dict])
async def list_bookmarks(conversation_id: str = PathParam(...)):
    """List bookmarks for a conversation."""
    if not check_database_initialized():
        return []
    
    import organization_api
    from backend.db import get_db_path
    return organization_api.list_bookmarks(str(get_db_path()), conversation_id)


@router.post("/conversations/{conversation_id}/bookmarks")
async def create_bookmark(conversation_id: str = PathParam(...), request: BookmarkRequest = Body(...)):
    """Create a bookmark."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    import organization_api
    from backend.db import get_db_path
    
    bookmark_id = organization_api.create_bookmark(str(get_db_path()), conversation_id, request.message_id, request.note)
    return {"bookmark_id": bookmark_id, "status": "created"}


@router.post("/conversations/{conversation_id}/star")
async def star_conversation(request: Request, conversation_id: str = PathParam(...)):
    """Star a conversation. Returns HTML fragment if HTMX request."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    import organization_api
    from backend.db import get_db_path
    
    # Check if already starred
    conn = get_db_connection()
    cursor = conn.execute("SELECT is_starred FROM conversations WHERE conversation_id = ?", (conversation_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    is_starred = bool(row[0])
    
    # Toggle star status
    if is_starred:
        organization_api.unstar_conversation(str(get_db_path()), conversation_id)
        new_starred = False
    else:
        organization_api.star_conversation(str(get_db_path()), conversation_id)
        new_starred = True
    
    conn.close()
    
    # Return HTML fragment if HTMX request - trigger conversation list reload
    if request.headers.get("HX-Request"):
        # Use HTMX trigger to reload the conversation list
        from fastapi.responses import Response
        response = Response(status_code=200)
        response.headers["HX-Trigger"] = "reloadConversations"
        return response
    
    return {"status": "starred" if new_starred else "unstarred"}


@router.delete("/conversations/{conversation_id}/star")
async def unstar_conversation(conversation_id: str = PathParam(...)):
    """Unstar a conversation."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    import organization_api
    from backend.db import get_db_path
    
    if organization_api.unstar_conversation(str(get_db_path()), conversation_id):
        return {"status": "unstarred"}
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.put("/conversations/{conversation_id}/title")
async def set_custom_title(conversation_id: str = PathParam(...), title: str = Body(..., embed=True)):
    """Set custom title for a conversation."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    import organization_api
    from backend.db import get_db_path
    
    if organization_api.set_custom_title(str(get_db_path()), conversation_id, title):
        return {"status": "updated"}
    raise HTTPException(status_code=404, detail="Conversation not found")

