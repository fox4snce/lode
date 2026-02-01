"""
FastAPI backend for Lode.
"""
from fastapi import FastAPI, HTTPException, Query, Path as PathParam, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import socket
from pathlib import Path
import sys
import os
import sqlite3
import uuid
import re
import io

from lode_version import __version__ as LODE_VERSION

# Add parent to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Also add current directory for table creation scripts
sys.path.insert(0, str(parent_dir))

from backend.db import check_database_initialized, initialize_database, get_db_connection, get_data_dir
from backend.jobs import create_job, get_job, list_jobs, cancel_job, JobType, JobStatus
from backend.routes import organization
from backend.routes import vectordb
from backend.feature_flags import is_feature_enabled

# Import route modules (they define routers)
from api.routes import conversations, messages, jobs

# Setup Jinja2 templates
templates_dir = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

# Add custom filters
def timestamp_filter(value):
    """Convert Unix timestamp to readable date."""
    if not value:
        return "Unknown"
    try:
        from datetime import datetime
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M")
    except:
        return str(value)

jinja_env.filters['timestamp'] = timestamp_filter
jinja_env.filters['date'] = timestamp_filter

# Highlight filter for showing search matches inside messages
def highlight_filter(value: str, query: str = ""):
    """
    Escape content then highlight occurrences of query (case-insensitive) using <mark>.
    Returns Markup-safe HTML.
    """
    try:
        from markupsafe import Markup, escape
    except Exception:
        # If MarkupSafe isn't available for some reason, fallback to plain text
        return value

    text = value or ""
    q = (query or "").strip()
    escaped = escape(text)

    if not q:
        return Markup(str(escaped).replace("\n", "<br>"))

    # Avoid pathological regex sizes; this is UI-only highlighting
    if len(q) > 200:
        return Markup(str(escaped).replace("\n", "<br>"))

    pattern = re.compile(re.escape(q), flags=re.IGNORECASE)
    highlighted = pattern.sub(lambda m: f'<mark class="search-hit">{m.group(0)}</mark>', str(escaped))
    highlighted = highlighted.replace("\n", "<br>")
    return Markup(highlighted)

jinja_env.filters["highlight"] = highlight_filter


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # On shutdown: signal running vectordb index jobs to stop so the process can exit
    try:
        from backend.job_runner import cancel_all_vectordb_jobs
        cancel_all_vectordb_jobs()
    except Exception:
        pass


def render_template(template_name: str, **context):
    """Render a Jinja2 template."""
    # Add feature flags to context for all templates
    from backend.feature_flags import is_feature_enabled
    context.setdefault('feature_flags', {
        'vectordb': is_feature_enabled('vectordb'),
        'chat': is_feature_enabled('chat'),
    })
    
    template = jinja_env.get_template(template_name)
    return template.render(**context)

app = FastAPI(title="Lode", version=LODE_VERSION, lifespan=lifespan)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# CORS for dev (pywebview)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    version: str = LODE_VERSION

class SetupCheckResponse(BaseModel):
    initialized: bool

class ConversationSummary(BaseModel):
    conversation_id: str
    title: Optional[str]
    create_time: Optional[float]
    update_time: Optional[float]
    message_count: int = 0
    word_count: int = 0
    ai_source: Optional[str]
    is_starred: bool = False
    tags: List[str] = []

class Message(BaseModel):
    message_id: str
    role: str
    content: str
    create_time: Optional[float]
    parent_id: Optional[str] = None

class SearchHit(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    role: str
    create_time: Optional[float]

class JobResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int = 0
    message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None

class ImportJobRequest(BaseModel):
    source_type: str  # "openai", "claude", or "lode"
    file_path: str
    calculate_stats: bool = True
    build_index: bool = True

class StateResponse(BaseModel):
    last_conversation_id: Optional[str] = None
    last_message_id: Optional[str] = None
    last_scroll_offset: Optional[int] = None

class StateRequest(BaseModel):
    last_conversation_id: Optional[str] = None
    last_message_id: Optional[str] = None
    last_scroll_offset: Optional[int] = None


# Core endpoints
@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")

@app.get("/api/setup/check", response_model=SetupCheckResponse)
async def setup_check():
    return SetupCheckResponse(initialized=check_database_initialized())

@app.post("/api/setup/initialize")
async def setup_initialize(request: Request):
    is_htmx = request.headers.get("HX-Request", "").lower() == "true"
    if check_database_initialized():
        raise HTTPException(status_code=400, detail="Database already initialized")

    def _escape_html(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    try:
        initialize_database()
        if is_htmx:
            # HX-Redirect makes the Welcome page reliably navigate after init.
            return HTMLResponse(
                '<div class="success">Database initialized. Opening Lode…</div>',
                status_code=200,
                headers={"HX-Redirect": "/main"},
            )
        return {"status": "success", "message": "Database initialized"}
    except Exception as e:
        if is_htmx:
            return HTMLResponse(
                f'<div class="error">Failed to initialize database: {_escape_html(str(e))}</div>',
                status_code=500,
            )
        raise HTTPException(status_code=500, detail=str(e))


# Favicon route
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon.ico"""
    favicon_path = static_dir / "img" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    raise HTTPException(status_code=404, detail="Favicon not found")

# HTML Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main entry point - redirects to appropriate screen."""
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("main.html"))

@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    """Welcome screen for first-time setup."""
    return HTMLResponse(render_template("welcome.html"))

@app.get("/main", response_class=HTMLResponse)
async def main_screen(request: Request):
    """Main application screen."""
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("main.html"))

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_screen(request: Request):
    """Analytics screen."""
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("analytics.html"))

@app.get("/import", response_class=HTMLResponse)
async def import_screen(request: Request):
    """Import screen."""
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("import.html"))

@app.get("/find-tools", response_class=HTMLResponse)
async def find_tools_screen(request: Request):
    """Find tools screen."""
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("find_tools.html"))

@app.get("/vectordb-search", response_class=HTMLResponse)
async def vectordb_search_screen(request: Request):
    """Vector search screen (Pro feature)."""
    if not is_feature_enabled("vectordb"):
        raise HTTPException(status_code=403, detail="Vector search is a Pro feature")
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("vectordb_search.html"))

@app.get("/chat", response_class=HTMLResponse)
async def chat_screen(request: Request):
    """Chat screen (Pro feature)."""
    if not is_feature_enabled("chat"):
        raise HTTPException(status_code=403, detail="Chat is a Pro feature")
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("chat.html"))

@app.get("/export", response_class=HTMLResponse)
async def export_screen(request: Request):
    """Export screen."""
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("export.html"))

@app.get("/settings", response_class=HTMLResponse)
async def settings_screen(request: Request):
    """Settings screen."""
    if not check_database_initialized():
        return HTMLResponse(render_template("welcome.html"))
    return HTMLResponse(render_template("settings.html"))


# Config API endpoints
@app.get("/api/config/port")
async def get_server_port():
    """Get configured server port."""
    from backend.config import get_port
    return {"port": get_port()}


class PortConfigRequest(BaseModel):
    port: int


@app.post("/api/config/port")
async def set_server_port(request: PortConfigRequest):
    """Set server port."""
    from backend.config import set_port
    
    if request.port < 1024 or request.port > 65535:
        raise HTTPException(status_code=400, detail="Port must be between 1024 and 65535")
    
    set_port(request.port)
    return {"status": "saved", "port": request.port}

@app.get("/help", response_class=HTMLResponse)
async def help_screen(request: Request):
    """Help screen."""
    return HTMLResponse(render_template("help.html"))

@app.get("/about", response_class=HTMLResponse)
async def about_screen(request: Request):
    """About screen."""
    return HTMLResponse(render_template("about.html"))


# Conversation endpoints
@app.get("/api/conversations")
async def list_conversations(
    request: Request,
    sort: str = Query("update_time"),
    q: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    starred: Optional[str] = Query(None),
    ai_source: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """List conversations with filtering and sorting. Returns HTML fragment if HTMX request."""
    if not check_database_initialized():
        if request.headers.get("HX-Request"):
            return HTMLResponse(render_template("fragments/conversation_list.html", conversations=[]))
        return []
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    
    # Use FTS5 search if query provided, otherwise regular query
    if q:
        # Check if FTS5 tables exist and use them
        try:
            import search_fts5
            from backend.db import get_db_path
            
            db_path = str(get_db_path())
            
            # First check if FTS5 tables exist
            conn_check = sqlite3.connect(db_path)
            cursor_check = conn_check.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('messages_fts', 'conversations_fts')
            """)
            fts_tables = [row[0] for row in cursor_check.fetchall()]
            conn_check.close()
            
            if len(fts_tables) < 2:
                # FTS5 tables don't exist, fall back to title search
                print(f"FTS5 tables not found, falling back to title search. Found tables: {fts_tables}")
                raise Exception("FTS5 tables not initialized")
            
            # Search conversations using FTS5
            fts_results = search_fts5.search_conversations(
                query=q,
                db_path=db_path,
                limit=limit,
                offset=offset
            )
            # Also search messages to find conversations
            msg_results = search_fts5.search_messages(
                query=q,
                db_path=db_path,
                limit=limit * 2,  # Get more to deduplicate
                offset=offset
            )
            
            # Collect unique conversation IDs
            conv_ids = set()
            for r in fts_results:
                conv_ids.add(r['conversation_id'])
            for r in msg_results:
                conv_ids.add(r['conversation_id'])
            
            if not conv_ids:
                # No results found - return empty but log for debugging
                print(f"FTS5 search for '{q}' returned 0 results")
                if request.headers.get("HX-Request"):
                    return HTMLResponse(render_template("fragments/conversation_list.html", conversations=[]))
                return []
            
            # Build query for those conversation IDs and apply other filters
            placeholders = ','.join('?' * len(conv_ids))
            query = f"""
                SELECT 
                    c.conversation_id,
                    c.title,
                    c.create_time,
                    c.update_time,
                    c.ai_source,
                    c.is_starred,
                    COALESCE(s.message_count_total, 0) as message_count,
                    COALESCE(s.word_count_total, 0) as word_count
                FROM conversations c
                LEFT JOIN conversation_stats s ON s.conversation_id = c.conversation_id
                WHERE c.conversation_id IN ({placeholders})
            """
            params = list(conv_ids)
            
            # Apply additional filters
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
            
            if starred == "true":
                query += " AND c.is_starred = 1"
            
            if ai_source and ai_source.strip():
                query += " AND c.ai_source = ?"
                params.append(ai_source)
            
            if date_from:
                query += " AND c.create_time >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND c.create_time <= ?"
                params.append(date_to)
        except Exception as e:
            # Fallback to title search if FTS5 fails
            print(f"FTS5 search error: {e}, falling back to title search")
            query = """
                SELECT 
                    c.conversation_id,
                    c.title,
                    c.create_time,
                    c.update_time,
                    c.ai_source,
                    c.is_starred,
                    COALESCE(s.message_count_total, 0) as message_count,
                    COALESCE(s.word_count_total, 0) as word_count
                FROM conversations c
                LEFT JOIN conversation_stats s ON s.conversation_id = c.conversation_id
                WHERE 1=1
            """
            params = []
            query += " AND c.title LIKE ?"
            params.append(f"%{q}%")
    else:
        query = """
            SELECT 
                c.conversation_id,
                c.title,
                c.create_time,
                c.update_time,
                c.ai_source,
                c.is_starred,
                COALESCE(s.message_count_total, 0) as message_count,
                COALESCE(s.word_count_total, 0) as word_count
            FROM conversations c
            LEFT JOIN conversation_stats s ON s.conversation_id = c.conversation_id
            WHERE 1=1
        """
        params = []
    
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
    
    if starred == "true":
        query += " AND c.is_starred = 1"
    
    if ai_source and ai_source.strip():  # Only filter if not empty
        query += " AND c.ai_source = ?"
        params.append(ai_source)
    
    if date_from:
        query += " AND c.create_time >= ?"
        params.append(date_from)
    
    if date_to:
        query += " AND c.create_time <= ?"
        params.append(date_to)
    
    # Calculate total count (same WHERE conditions, no LIMIT/OFFSET/ORDER BY)
    # Build count query by extracting FROM and WHERE parts
    from_where = query.split("FROM", 1)[1].split("ORDER BY")[0] if "ORDER BY" in query else query.split("FROM", 1)[1]
    count_query = "SELECT COUNT(*) as total FROM" + from_where
    count_cursor = conn.execute(count_query, params)
    total_count = count_cursor.fetchone()['total']
    
    sort_map = {
        "update_time": "c.update_time DESC NULLS LAST",
        "create_time": "c.create_time ASC NULLS LAST",
        "message_count": "s.message_count_total DESC NULLS LAST",
        "word_count": "s.word_count_total DESC NULLS LAST"
    }
    
    # Apply sorting and pagination
    query += f" ORDER BY {sort_map.get(sort, 'c.update_time DESC NULLS LAST')}"
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        conv_id = row['conversation_id']
        tag_cursor = conn.execute("""
            SELECT t.name FROM tags t
            JOIN conversation_tags ct ON ct.tag_id = t.tag_id
            WHERE ct.conversation_id = ?
        """, (conv_id,))
        tags = [r[0] for r in tag_cursor.fetchall()]
        
        results.append({
            "conversation_id": conv_id,
            "title": row['title'],
            "create_time": row['create_time'],
            "update_time": row['update_time'],
            "message_count": row['message_count'] or 0,
            "word_count": row['word_count'] or 0,
            "ai_source": row['ai_source'],
            "is_starred": bool(row['is_starred']),
            "tags": tags
        })
    
    conn.close()
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(render_template(
            "fragments/conversation_list.html", 
            conversations=results,
            total_count=total_count,
            offset=offset,
            limit=limit,
            has_more=(offset + limit < total_count)
        ))
    return results

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(request: Request, conversation_id: str = PathParam(...)):
    """Get conversation details. Returns HTML fragment if HTMX request."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    tag_cursor = conn.execute("""
        SELECT t.name FROM tags t
        JOIN conversation_tags ct ON ct.tag_id = t.tag_id
        WHERE ct.conversation_id = ?
    """, (conversation_id,))
    tags = [r[0] for r in tag_cursor.fetchall()]
    
    stats_cursor = conn.execute("SELECT * FROM conversation_stats WHERE conversation_id = ?", (conversation_id,))
    stats_row = stats_cursor.fetchone()
    stats = dict(stats_row) if stats_row else None
    
    result = {
        "conversation_id": row['conversation_id'],
        "title": row['title'],
        "create_time": row['create_time'],
        "update_time": row['update_time'],
        "ai_source": row['ai_source'],
        "is_starred": bool(row['is_starred']),
        "tags": tags,
        "stats": stats
    }
    conn.close()
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(render_template("fragments/conversation_details.html", conversation=result))
    return result

@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages(
    request: Request,
    conversation_id: str = PathParam(...),
    anchor_message_id: Optional[str] = Query(None),
    direction: str = Query("around", pattern="^(older|newer|around)$"),
    # NOTE: This is a local desktop-style app; UX expectation is often “load the whole chat”.
    # Allow larger limits so the frontend can request full conversations.
    limit: int = Query(200, ge=1, le=50000),
    q: Optional[str] = Query(None),
):
    """Get messages with windowing support. Returns HTML fragment if HTMX request."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    
    # Verify conversation exists
    cursor = conn.execute("SELECT conversation_id FROM conversations WHERE conversation_id = ?", (conversation_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if anchor_message_id:
        cursor = conn.execute("""
            SELECT id, create_time FROM messages
            WHERE conversation_id = ? AND message_id = ?
        """, (conversation_id, anchor_message_id))
        anchor = cursor.fetchone()
        if not anchor:
            conn.close()
            raise HTTPException(status_code=404, detail="Anchor message not found")
        anchor_id = anchor['id']
        anchor_time = anchor['create_time']
        
        if direction == "around":
            cursor = conn.execute("""
                SELECT message_id, role, content, create_time, parent_id
                FROM messages
                WHERE conversation_id = ?
                    AND ((create_time = ? AND id <= ?) OR (create_time < ?) OR (create_time > ?))
                ORDER BY create_time ASC, id ASC
                LIMIT ?
            """, (conversation_id, anchor_time, anchor_id, anchor_time, anchor_time, limit))
        elif direction == "older":
            cursor = conn.execute("""
                SELECT message_id, role, content, create_time, parent_id
                FROM messages
                WHERE conversation_id = ? AND (create_time < ? OR (create_time = ? AND id < ?))
                ORDER BY create_time DESC, id DESC
                LIMIT ?
            """, (conversation_id, anchor_time, anchor_time, anchor_id, limit))
        else:
            cursor = conn.execute("""
                SELECT message_id, role, content, create_time, parent_id
                FROM messages
                WHERE conversation_id = ? AND (create_time > ? OR (create_time = ? AND id > ?))
                ORDER BY create_time ASC, id ASC
                LIMIT ?
            """, (conversation_id, anchor_time, anchor_time, anchor_id, limit))
    else:
        cursor = conn.execute("""
            SELECT message_id, role, content, create_time, parent_id
            FROM messages
            WHERE conversation_id = ?
            ORDER BY create_time ASC, id ASC
            LIMIT ?
        """, (conversation_id, limit))
    
    rows = cursor.fetchall()
    if direction == "older":
        rows = list(reversed(rows))
    
    messages = []
    for row in rows:
        msg = {
            "message_id": row['message_id'],
            "role": row['role'],
            "content": row['content'] or '',
            "create_time": row['create_time'],
        }
        # parent_id might be None, handle it safely
        try:
            msg["parent_id"] = row['parent_id']
        except (KeyError, IndexError):
            msg["parent_id"] = None
        messages.append(msg)
    
    conn.close()
    
    # Return HTML fragment if HTMX request
    if request.headers.get("HX-Request"):
        return HTMLResponse(render_template("fragments/message_list.html", messages=messages, search_query=q or ""))
    return messages

@app.get("/api/messages/{message_id}/context", response_model=List[Message])
async def get_message_context(
    message_id: str = PathParam(...),
    n: int = Query(5, ge=1, le=50)
):
    """Get context around a message."""
    try:
        import search_fts5
        from backend.db import get_db_path
        
        # Find message to get conversation_id
        conn = get_db_connection()
        cursor = conn.execute("""
            SELECT conversation_id FROM messages WHERE message_id = ?
        """, (message_id,))
        msg = cursor.fetchone()
        conn.close()
        
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        
        conv_id = msg['conversation_id']
        
        # Use search_fts5's get_message_context
        context = search_fts5.get_message_context(
            str(get_db_path()),
            conv_id,
            message_id,
            context_before=n,
            context_after=n
        )
        
        # Combine before, target, and after
        all_messages = []
        if context.get('before'):
            all_messages.extend(context['before'])
        if context.get('target'):
            all_messages.append(context['target'])
        if context.get('after'):
            all_messages.extend(context['after'])
        
        return [
            Message(
                message_id=m['message_id'],
                role=m['role'],
                content=m['content'],
                create_time=m['create_time'],
                parent_id=m.get('parent_id')
            )
            for m in all_messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Search endpoint
@app.get("/api/search", response_model=List[SearchHit])
async def search(
    q: str = Query(..., min_length=1),
    conversation_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Full-text search using FTS5."""
    if not check_database_initialized():
        return []
    
    try:
        # Import search_fts5 from project root
        import importlib.util
        search_fts5_path = parent_dir / "search_fts5.py"
        if search_fts5_path.exists():
            spec = importlib.util.spec_from_file_location("search_fts5", search_fts5_path)
            search_fts5 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(search_fts5)
        else:
            # Fallback: try direct import
            import search_fts5
        
        from backend.db import get_db_path
        
        results = search_fts5.search_messages(
            query=q,
            db_path=str(get_db_path()),
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
        
        return [
            SearchHit(
                conversation_id=r['conversation_id'],
                message_id=r['message_id'],
                content=r['content'],
                role=r['role'],
                create_time=r['create_time']
            )
            for r in results
        ]
    except Exception as e:
        # Log error for debugging
        import traceback
        print(f"Search error: {e}")
        print(traceback.format_exc())
        # If FTS5 tables don't exist, return empty
        return []


# Job endpoints
@app.post("/api/jobs/import", response_model=JobResponse)
async def create_import_job(request: ImportJobRequest):
    """Create an import job."""
    job_id = create_job(JobType.IMPORT.value, {
        "source_type": request.source_type,
        "file_path": request.file_path,
        "calculate_stats": request.calculate_stats,
        "build_index": request.build_index
    })
    
    # Start import in background
    import asyncio
    from backend.job_runner import run_import_job
    asyncio.create_task(run_import_job(job_id, {
        "source_type": request.source_type,
        "file_path": request.file_path,
        "calculate_stats": request.calculate_stats,
        "build_index": request.build_index
    }))
    
    return JobResponse(job_id=job_id)


@app.post("/api/jobs/import-upload", response_model=JobResponse)
async def create_import_upload_job(
    source_type: str = Form(...),
    calculate_stats: bool = Form(True),
    build_index: bool = Form(True),
    upload: UploadFile = File(...),
):
    """Create an import job from an uploaded file (recommended for webview/browser)."""
    if source_type not in ("openai", "claude", "lode"):
        raise HTTPException(status_code=400, detail="source_type must be 'openai', 'claude', or 'lode'")

    # Persist upload to a local file so the existing job runner/importers can consume it.
    # IMPORTANT: when packaged, write to the persistent user data directory (not the temp extraction dir).
    uploads_dir = get_data_dir() / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    safe_name = (upload.filename or "upload.json").replace("\\", "_").replace("/", "_")
    saved_name = f"{uuid.uuid4().hex}_{safe_name}"
    saved_path = uploads_dir / saved_name

    try:
        contents = await upload.read()
        saved_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    # Create job
    job_id = create_job(JobType.IMPORT.value, metadata={
        "source_type": source_type,
        "file_path": str(saved_path),
        "original_filename": upload.filename,
        "calculate_stats": calculate_stats,
        "build_index": build_index,
    })

    # Start import in background
    import asyncio
    from backend.job_runner import run_import_job
    asyncio.create_task(run_import_job(job_id, {
        "source_type": source_type,
        "file_path": str(saved_path),
        "calculate_stats": calculate_stats,
        "build_index": build_index,
    }))

    return JobResponse(job_id=job_id)

@app.post("/api/jobs/reindex", response_model=JobResponse)
async def create_reindex_job():
    """Create a reindex job."""
    job_id = create_job(JobType.REINDEX.value)
    
    # Start reindex in background
    import asyncio
    from backend.job_runner import run_reindex_job
    asyncio.create_task(run_reindex_job(job_id))
    
    return JobResponse(job_id=job_id)


class VectordbIndexRequest(BaseModel):
    conversation_ids: Optional[List[str]] = None

@app.post("/api/jobs/vectordb-index", response_model=JobResponse)
async def create_vectordb_index_job(request: VectordbIndexRequest = VectordbIndexRequest()):
    """Create a vectordb indexing job."""
    from backend.vectordb import service as vectordb_service
    ready, message = vectordb_service.embedder_model_ready()
    if not ready:
        raise HTTPException(status_code=400, detail=message)
    job_id = create_job(JobType.VECTORDB_INDEX.value, {
        "conversation_ids": request.conversation_ids,  # None = all conversations
    })
    import asyncio
    from backend.job_runner import run_vectordb_index_job
    asyncio.create_task(run_vectordb_index_job(job_id, {
        "conversation_ids": request.conversation_ids,
    }))
    return JobResponse(job_id=job_id)

@app.get("/api/jobs", response_model=List[JobStatusResponse])
async def list_jobs_endpoint():
    """List all jobs."""
    jobs = list_jobs()
    return [JobStatusResponse(**job) for job in jobs]

@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_endpoint(job_id: str = PathParam(...)):
    """Get job status."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job)

@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str = PathParam(...)):
    """Cancel a job."""
    from backend.job_runner import set_vectordb_job_cancelled
    if cancel_job(job_id):
        set_vectordb_job_cancelled(job_id)  # signal running indexer to stop
        return {"status": "cancelled"}
    raise HTTPException(status_code=400, detail="Job cannot be cancelled")


# State endpoints
@app.get("/api/state", response_model=StateResponse)
async def get_state():
    """Get application state."""
    if not check_database_initialized():
        return StateResponse()
    
    try:
        import continue_feature
        from backend.db import get_db_path
        
        state = continue_feature.get_last_conversation(str(get_db_path()))
        if state:
            return StateResponse(
                last_conversation_id=state.get('conversation_id'),
                last_message_id=state.get('message_id'),
                last_scroll_offset=state.get('scroll_offset')
            )
    except:
        pass
    
    return StateResponse()

@app.post("/api/state")
async def save_state(request: StateRequest):
    """Save application state."""
    if not check_database_initialized():
        return {"status": "database_not_initialized"}
    
    try:
        import continue_feature
        from backend.db import get_db_path
        
        continue_feature.save_last_conversation(
            str(get_db_path()),
            request.last_conversation_id or '',
            request.last_message_id,
            request.last_scroll_offset
        )
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Analytics endpoints
@app.post("/api/analytics/refresh")
async def refresh_analytics():
    """
    Recompute ALL analytics once and store results in the DB cache.

    After this completes, all analytics endpoints will serve cached results
    until the next refresh.
    """
    if not check_database_initialized():
        return {"status": "not_initialized"}

    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import clear_cache, set_cached

        db_path = str(get_db_path())
        conn = sqlite3.connect(db_path)

        clear_cache(conn)

        # Usage: day/week/month (no explicit range)
        for p in ("day", "week", "month"):
            set_cached(conn, f"usage:{p}", analytics.usage_over_time(db_path=db_path, period=p))

        # Streaks
        set_cached(conn, "streaks", analytics.longest_streak(db_path))

        # Top words/phrases (UI defaults)
        # Note: bump cache key when filtering behavior changes.
        set_cached(conn, "top_words_v3:50", analytics.top_words(db_path, limit=50))
        set_cached(conn, "top_phrases:30", analytics.top_phrases(db_path, limit=30))

        # Vocabulary (UI default)
        set_cached(conn, "vocabulary:month", analytics.vocabulary_size_trend(db_path, period="month"))

        # Response ratio + heatmap
        set_cached(conn, "response_ratio", analytics.response_ratio(db_path))
        set_cached(conn, "heatmap", analytics.time_of_day_heatmap(db_path))

        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        print(f"Analytics refresh error: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/usage")
async def get_usage_over_time(
    period: str = Query("day", pattern="^(day|week|month)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get usage statistics over time."""
    if not check_database_initialized():
        return []
    
    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import get_cached, set_cached
        from datetime import datetime
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        db_path = str(get_db_path())

        # Cache only the canonical "no explicit date range" query.
        if not start and not end:
            conn = sqlite3.connect(db_path)
            cached = get_cached(conn, f"usage:{period}")
            if cached is not None:
                conn.close()
                return cached

            results = analytics.usage_over_time(db_path=db_path, period=period)
            set_cached(conn, f"usage:{period}", results)
            conn.commit()
            conn.close()
            return results

        # Range queries are computed on demand (not cached).
        return analytics.usage_over_time(db_path=db_path, period=period, start_date=start, end_date=end)
    except Exception as e:
        print(f"Analytics error: {e}")
        return []

@app.get("/api/analytics/streaks")
async def get_longest_streak():
    """Get longest streak of consecutive days."""
    if not check_database_initialized():
        return {}
    
    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import get_cached, set_cached

        db_path = str(get_db_path())
        conn = sqlite3.connect(db_path)
        cached = get_cached(conn, "streaks")
        if cached is not None:
            conn.close()
            return cached

        result = analytics.longest_streak(db_path)
        set_cached(conn, "streaks", result)
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        print(f"Analytics error: {e}")
        return {}

@app.get("/api/analytics/top-words")
async def get_top_words(limit: int = Query(50, ge=1, le=200)):
    """Get top words."""
    if not check_database_initialized():
        return []
    
    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import get_cached, set_cached

        db_path = str(get_db_path())
        # Note: bump cache key when filtering behavior changes.
        cache_key = f"top_words_v3:{limit}"
        conn = sqlite3.connect(db_path)
        cached = get_cached(conn, cache_key)
        if cached is not None:
            conn.close()
            return cached

        results = analytics.top_words(db_path, limit=limit)
        set_cached(conn, cache_key, results)
        conn.commit()
        conn.close()
        return results
    except Exception as e:
        print(f"Analytics error: {e}")
        return []

@app.get("/api/analytics/top-phrases")
async def get_top_phrases(limit: int = Query(30, ge=1, le=100)):
    """Get top phrases."""
    if not check_database_initialized():
        return []
    
    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import get_cached, set_cached

        db_path = str(get_db_path())
        cache_key = f"top_phrases:{limit}"
        conn = sqlite3.connect(db_path)
        cached = get_cached(conn, cache_key)
        if cached is not None:
            conn.close()
            return cached

        results = analytics.top_phrases(db_path, limit=limit)
        set_cached(conn, cache_key, results)
        conn.commit()
        conn.close()
        return results
    except Exception as e:
        print(f"Analytics error: {e}")
        return []

@app.get("/api/analytics/vocabulary")
async def get_vocabulary_trend(period: str = Query("month", pattern="^(day|week|month)$")):
    """Get vocabulary size trend."""
    if not check_database_initialized():
        return []
    
    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import get_cached, set_cached

        db_path = str(get_db_path())
        cache_key = f"vocabulary:{period}"
        conn = sqlite3.connect(db_path)
        cached = get_cached(conn, cache_key)
        if cached is not None:
            conn.close()
            return cached

        results = analytics.vocabulary_size_trend(db_path, period=period)
        set_cached(conn, cache_key, results)
        conn.commit()
        conn.close()
        return results
    except Exception as e:
        print(f"Analytics error: {e}")
        return []

@app.get("/api/analytics/response-ratio")
async def get_response_ratio():
    """Get user vs assistant response ratio."""
    if not check_database_initialized():
        return {}
    
    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import get_cached, set_cached

        db_path = str(get_db_path())
        conn = sqlite3.connect(db_path)
        cached = get_cached(conn, "response_ratio")
        if cached is not None:
            conn.close()
            return cached

        result = analytics.response_ratio(db_path)
        set_cached(conn, "response_ratio", result)
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        print(f"Analytics error: {e}")
        return {}

@app.get("/api/analytics/heatmap")
async def get_time_of_day_heatmap():
    """Get time-of-day activity heatmap."""
    if not check_database_initialized():
        return []
    
    try:
        import analytics
        from backend.db import get_db_path
        from backend.analytics_cache import get_cached, set_cached

        db_path = str(get_db_path())
        conn = sqlite3.connect(db_path)
        cached = get_cached(conn, "heatmap")
        if cached is not None:
            conn.close()
            return cached

        results = analytics.time_of_day_heatmap(db_path)
        set_cached(conn, "heatmap", results)
        conn.commit()
        conn.close()
        return results
    except Exception as e:
        print(f"Analytics error: {e}")
        return []

# Find Tools endpoints
@app.get("/api/find/code")
async def find_code_blocks(limit: int = Query(100, ge=1, le=500)):
    """Find all code blocks."""
    if not check_database_initialized():
        return []
    
    try:
        import find_tools
        from backend.db import get_db_path
        results = find_tools.find_code_blocks(str(get_db_path()), limit=limit)
        return results
    except Exception as e:
        print(f"Find tools error: {e}")
        return []

@app.get("/api/find/links")
async def find_links(limit: int = Query(100, ge=1, le=500)):
    """Find all links."""
    if not check_database_initialized():
        return []
    
    try:
        import find_tools
        from backend.db import get_db_path
        result = find_tools.find_links(str(get_db_path()), limit=limit)
        # find_links returns a dict with 'links' key, extract just the links array
        if isinstance(result, dict) and 'links' in result:
            return result['links']
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"Find tools error: {e}")
        import traceback
        traceback.print_exc()
        return []

@app.get("/api/find/todos")
async def find_todos(limit: int = Query(100, ge=1, le=500)):
    """Find all TODOs."""
    if not check_database_initialized():
        return []
    
    try:
        import find_tools
        from backend.db import get_db_path
        results = find_tools.find_todos(str(get_db_path()), limit=limit)
        return results
    except Exception as e:
        print(f"Find tools error: {e}")
        return []

@app.get("/api/find/questions")
async def find_questions(limit: int = Query(100, ge=1, le=500)):
    """Find all questions."""
    if not check_database_initialized():
        return []
    
    try:
        import find_tools
        from backend.db import get_db_path
        results = find_tools.find_questions(str(get_db_path()), limit=limit)
        return results
    except Exception as e:
        print(f"Find tools error: {e}")
        return []

@app.get("/api/find/dates")
async def find_dates(limit: int = Query(100, ge=1, le=500)):
    """Find all dates mentioned."""
    if not check_database_initialized():
        return []
    
    try:
        import find_tools
        from backend.db import get_db_path
        results = find_tools.find_dates(str(get_db_path()), limit=limit)
        return results
    except Exception as e:
        print(f"Find tools error: {e}")
        return []

@app.get("/api/find/decisions")
async def find_decisions(limit: int = Query(100, ge=1, le=500)):
    """Find all decisions."""
    if not check_database_initialized():
        return []
    
    try:
        import find_tools
        from backend.db import get_db_path
        results = find_tools.find_decisions(str(get_db_path()), limit=limit)
        return results
    except Exception as e:
        print(f"Find tools error: {e}")
        return []

@app.get("/api/find/prompts")
async def find_prompts(limit: int = Query(100, ge=1, le=500)):
    """Find all prompts."""
    if not check_database_initialized():
        return []
    
    try:
        import find_tools
        from backend.db import get_db_path
        results = find_tools.find_prompts(str(get_db_path()), limit=limit)
        return results
    except Exception as e:
        print(f"Find tools error: {e}")
        return []

# Integrity Check endpoints
@app.get("/api/integrity/check")
async def run_integrity_checks():
    """Run all integrity checks."""
    if not check_database_initialized():
        return {}
    
    try:
        import integrity_checks
        from backend.db import get_db_path
        results = integrity_checks.check_integrity(str(get_db_path()))
        return results
    except Exception as e:
        print(f"Integrity check error: {e}")
        import traceback
        traceback.print_exc()
        return {}

# Deduplication endpoints
@app.get("/api/deduplication/find-messages")
async def find_duplicate_messages(conversation_id: Optional[str] = Query(None)):
    """Find duplicate messages."""
    if not check_database_initialized():
        return []
    
    try:
        import deduplication_tool
        from backend.db import get_db_path
        results = deduplication_tool.find_duplicate_messages(str(get_db_path()), conversation_id)
        return results
    except Exception as e:
        print(f"Deduplication error: {e}")
        return []

@app.get("/api/deduplication/find-conversations")
async def find_duplicate_conversations():
    """Find duplicate conversations."""
    if not check_database_initialized():
        return []
    
    try:
        import deduplication_tool
        from backend.db import get_db_path
        results = deduplication_tool.find_duplicate_conversations(str(get_db_path()))
        return results
    except Exception as e:
        print(f"Deduplication error: {e}")
        return []

@app.get("/api/deduplication/stats")
async def get_deduplication_stats():
    """Get deduplication statistics."""
    if not check_database_initialized():
        return {}
    
    try:
        import deduplication_tool
        from backend.db import get_db_path
        results = deduplication_tool.get_deduplication_stats(str(get_db_path()))
        return results
    except Exception as e:
        print(f"Deduplication error: {e}")
        return {}

# Cleanup endpoints
@app.get("/api/cleanup/files")
async def list_imported_files(import_batch_id: Optional[str] = Query(None)):
    """List imported files."""
    if not check_database_initialized():
        return []
    
    try:
        import wipe_imported_files
        from backend.db import get_db_path
        results = wipe_imported_files.list_imported_files(str(get_db_path()), import_batch_id)
        return results
    except Exception as e:
        print(f"Cleanup error: {e}")
        return []

@app.post("/api/cleanup/wipe-files")
async def wipe_files(
    import_batch_id: Optional[str] = None,
    verify: bool = True,
    dry_run: bool = False,
    wipe_database: bool = True
):
    """Wipe imported files and optionally database data."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    try:
        import wipe_imported_files
        from backend.db import get_db_path
        result = wipe_imported_files.wipe_imported_files(
            str(get_db_path()),
            import_batch_id,
            verify=verify,
            dry_run=dry_run,
            wipe_database=wipe_database
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Import Reports endpoints
@app.get("/api/import/reports")
async def list_import_reports(limit: int = Query(10, ge=1, le=100)):
    """List all import reports."""
    if not check_database_initialized():
        return []
    
    try:
        import import_report
        from backend.db import get_db_path
        results = import_report.list_import_reports(str(get_db_path()), limit=limit)
        return results
    except Exception as e:
        print(f"Import reports error: {e}")
        return []

@app.get("/api/import/reports/{batch_id}")
async def get_import_report(batch_id: str = PathParam(...)):
    """Get import report details."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    try:
        import import_report
        from backend.db import get_db_path
        result = import_report.get_import_report(str(get_db_path()), batch_id)
        if not result:
            raise HTTPException(status_code=404, detail="Import report not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Export endpoints
@app.post("/api/export/conversation/{conversation_id}")
async def export_conversation(
    conversation_id: str = PathParam(...),
    format: str = Query("markdown", pattern="^(markdown|csv|json)$"),
    include_timestamps: bool = Query(True),
    include_metadata: bool = Query(True)
):
    """Export a conversation to a file in the persistent exports directory."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    try:
        import export_tools
        from backend.db import get_db_path, get_db_connection
        from datetime import datetime
        import json
        import csv
        
        # Create exports directory if it doesn't exist.
        # IMPORTANT: when packaged, write to the persistent user data directory (not the temp extraction dir).
        exports_dir = get_data_dir() / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        # Get conversation title for filename
        conn = get_db_connection()
        cursor = conn.execute("SELECT title FROM conversations WHERE conversation_id = ?", (conversation_id,))
        conv_row = cursor.fetchone()
        if not conv_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get custom title if exists
        cursor = conn.execute("SELECT custom_title FROM custom_titles WHERE conversation_id = ?", (conversation_id,))
        custom_title_row = cursor.fetchone()
        display_title = custom_title_row[0] if custom_title_row else conv_row[0] or 'conversation'
        conn.close()
        
        # Sanitize filename
        sanitized = re.sub(r'[^a-z0-9]', '_', display_title.lower())
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine file extension and generate content
        if format == "markdown":
            extension = ".md"
            content = export_tools.export_conversation_to_markdown(
                str(get_db_path()),
                conversation_id,
                include_timestamps=include_timestamps,
                include_metadata=include_metadata
            )
        elif format == "json":
            extension = ".json"
            conn = get_db_connection()
            cursor = conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,))
            conv = dict(cursor.fetchone())
            cursor = conn.execute("""
                SELECT message_id, role, content, create_time, parent_id
                FROM messages
                WHERE conversation_id = ?
                ORDER BY create_time ASC, id ASC
            """, (conversation_id,))
            msgs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            data = {
                "lode_export_format_version": "1.0",
                "conversation": dict(conv),
                "messages": [dict(m) for m in msgs]
            }
            content = json.dumps(data, indent=2, ensure_ascii=False)
        else:  # CSV
            extension = ".csv"
            conn = get_db_connection()
            cursor = conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,))
            conv = dict(cursor.fetchone())
            cursor = conn.execute("""
                SELECT message_id, role, content, create_time, parent_id
                FROM messages
                WHERE conversation_id = ?
                ORDER BY create_time ASC, id ASC
            """, (conversation_id,))
            msgs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            # Generate CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write conversation metadata as header rows if metadata included
            if include_metadata:
                writer.writerow(["Field", "Value"])
                writer.writerow(["Conversation ID", conv.get('conversation_id', '')])
                writer.writerow(["Title", conv.get('title', '')])
                writer.writerow(["AI Source", conv.get('ai_source', '')])
                writer.writerow(["Create Time", conv.get('create_time', '')])
                writer.writerow(["Update Time", conv.get('update_time', '')])
                writer.writerow([])  # Empty row separator
            
            # Write messages
            writer.writerow(["Message ID", "Role", "Content", "Create Time", "Parent ID"])
            for msg in msgs:
                msg_content = msg.get('content', '').replace('\n', ' ').replace('\r', ' ')
                create_time = msg.get('create_time', '') if include_timestamps else ''
                writer.writerow([
                    msg.get('message_id', ''),
                    msg.get('role', ''),
                    msg_content,
                    create_time,
                    msg.get('parent_id', '') or ''
                ])
            
            content = output.getvalue()
            output.close()
        
        # Write file to exports directory
        filename = f"{sanitized}_{conversation_id[:8]}_{timestamp}{extension}"
        file_path = exports_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Return file path relative to the Lode data dir (forward slashes for cross-platform / Windows).
        relative_path = file_path.relative_to(get_data_dir())
        path_str = str(relative_path).replace("\\", "/")
        
        return {
            "format": format,
            "filename": filename,
            "path": path_str,
            "absolute_path": str(file_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/file/{file_path:path}")
async def get_exported_file(file_path: str):
    """Get exported file content for preview."""
    try:
        # Normalize path (Windows may send backslashes)
        file_path = file_path.replace("\\", "/")
        # Security: only allow files from exports/, no traversal
        if not file_path.startswith("exports/") or ".." in file_path:
            raise HTTPException(status_code=403, detail="Access denied")
        
        file_path_obj = get_data_dir() / file_path
        if not file_path_obj.exists() or not file_path_obj.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return file content as text (used by Export page preview)
        from fastapi.responses import PlainTextResponse
        content = file_path_obj.read_text(encoding="utf-8", errors="replace")
        return PlainTextResponse(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/open-exports-folder")
async def open_exports_folder():
    """Open the exports directory in the system file manager."""
    try:
        import subprocess
        exports_dir = get_data_dir() / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        path = str(exports_dir.resolve())
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Include routers
app.include_router(organization.router)
# VectorDB router (Pro feature)
if is_feature_enabled("vectordb"):
    app.include_router(vectordb.router)
# Chat router (Pro feature)
if is_feature_enabled("chat"):
    from backend.routes import chat
    app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(jobs.router)

# HTML routes are defined above - no longer using React/Vite


if __name__ == "__main__":
    import uvicorn
    port = 8000
    print(f"Starting server on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)

