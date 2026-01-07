"""
FastAPI backend for Lode.
"""
from fastapi import FastAPI, HTTPException, Query, Path as PathParam, Request
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

# Add parent to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Also add current directory for table creation scripts
sys.path.insert(0, str(parent_dir))

from backend.db import check_database_initialized, initialize_database, get_db_connection
from backend.jobs import create_job, get_job, list_jobs, cancel_job, JobType, JobStatus
from backend.routes import organization

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

def render_template(template_name: str, **context):
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)

app = FastAPI(title="Lode", version="1.0.0")

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
    version: str = "1.0.0"

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
    source_type: str  # "openai" or "claude"
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
async def setup_initialize():
    if check_database_initialized():
        raise HTTPException(status_code=400, detail="Database already initialized")
    
    try:
        initialize_database()
        return {"status": "success", "message": "Database initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List conversations with filtering and sorting. Returns HTML fragment if HTMX request."""
    if not check_database_initialized():
        if request.headers.get("HX-Request"):
            return HTMLResponse(render_template("fragments/conversation_list.html", conversations=[]))
        return []
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    
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
    
    if q:
        query += " AND c.title LIKE ?"
        params.append(f"%{q}%")
    
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
    
    if ai_source:
        query += " AND c.ai_source = ?"
        params.append(ai_source)
    
    if date_from:
        query += " AND c.create_time >= ?"
        params.append(date_from)
    
    if date_to:
        query += " AND c.create_time <= ?"
        params.append(date_to)
    
    sort_map = {
        "update_time": "c.update_time DESC NULLS LAST",
        "create_time": "c.create_time ASC NULLS LAST",
        "message_count": "s.message_count_total DESC NULLS LAST",
        "word_count": "s.word_count_total DESC NULLS LAST"
    }
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
        return HTMLResponse(render_template("fragments/conversation_list.html", conversations=results))
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
    limit: int = Query(200, ge=1, le=1000)
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
    
    messages = [{
        "message_id": row['message_id'],
        "role": row['role'],
        "content": row['content'] or '',
        "create_time": row['create_time'],
        "parent_id": row.get('parent_id')
    } for row in rows]
    
    conn.close()
    
    # Return HTML fragment if HTMX request
    if request.headers.get("HX-Request"):
        return HTMLResponse(render_template("fragments/message_list.html", messages=messages))
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

@app.post("/api/jobs/reindex", response_model=JobResponse)
async def create_reindex_job():
    """Create a reindex job."""
    job_id = create_job(JobType.REINDEX.value)
    
    # Start reindex in background
    import asyncio
    from backend.job_runner import run_reindex_job
    asyncio.create_task(run_reindex_job(job_id))
    
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
    if cancel_job(job_id):
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
        from datetime import datetime
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        results = analytics.usage_over_time(
            db_path=str(get_db_path()),
            period=period,
            start_date=start,
            end_date=end
        )
        return results
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
        result = analytics.longest_streak(str(get_db_path()))
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
        results = analytics.top_words(str(get_db_path()), limit=limit)
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
        results = analytics.top_phrases(str(get_db_path()), limit=limit)
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
        results = analytics.vocabulary_size_trend(str(get_db_path()), period=period)
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
        result = analytics.response_ratio(str(get_db_path()))
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
        results = analytics.time_of_day_heatmap(str(get_db_path()))
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
    dry_run: bool = False
):
    """Wipe imported files."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    try:
        import wipe_imported_files
        from backend.db import get_db_path
        result = wipe_imported_files.wipe_imported_files(
            str(get_db_path()),
            import_batch_id,
            verify=verify,
            dry_run=dry_run
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
    """Export a conversation."""
    if not check_database_initialized():
        raise HTTPException(status_code=400, detail="Database not initialized")
    
    try:
        import export_tools
        from backend.db import get_db_path
        
        if format == "markdown":
            content = export_tools.export_conversation_to_markdown(
                str(get_db_path()),
                conversation_id,
                include_timestamps=include_timestamps,
                include_metadata=include_metadata
            )
            return {"format": "markdown", "content": content}
        else:
            # For CSV/JSON, return structured data
            from backend.db import get_db_connection
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
            
            if format == "json":
                return {"conversation": dict(conv), "messages": [dict(m) for m in msgs]}
            else:  # CSV
                # Return as structured data, frontend can convert
                return {"format": "csv", "conversation": dict(conv), "messages": [dict(m) for m in msgs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include routers
app.include_router(organization.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(jobs.router)

# HTML routes are defined above - no longer using React/Vite


if __name__ == "__main__":
    import uvicorn
    port = 8000
    print(f"Starting server on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)

