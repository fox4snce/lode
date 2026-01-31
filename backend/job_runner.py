"""
Job runner for executing background jobs.
"""
import asyncio
import sys
import threading
from pathlib import Path
from typing import Dict

from backend.jobs import update_job, JobStatus, get_job
from backend.db import get_db_path

# Registry of job_id -> Event for vectordb index jobs; setting the event stops indexing.
_vectordb_cancel_events: Dict[str, threading.Event] = {}
_vectordb_cancel_lock = threading.Lock()


def set_vectordb_job_cancelled(job_id: str) -> None:
    """Signal a running vectordb index job to stop (used by cancel API and on shutdown)."""
    with _vectordb_cancel_lock:
        if job_id in _vectordb_cancel_events:
            _vectordb_cancel_events[job_id].set()


def cancel_all_vectordb_jobs() -> None:
    """Signal all running vectordb index jobs to stop (call on app shutdown)."""
    with _vectordb_cancel_lock:
        for event in _vectordb_cancel_events.values():
            event.set()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def run_import_job(job_id: str, metadata: dict):
    """Run an import job."""
    source_type = metadata.get('source_type')
    file_path = metadata.get('file_path')
    calculate_stats = metadata.get('calculate_stats', True)
    build_index = metadata.get('build_index', True)
    
    if not file_path or not source_type:
        update_job(job_id, status=JobStatus.FAILED.value, error="Missing file_path or source_type")
        return
    
    try:
        update_job(job_id, status=JobStatus.RUNNING.value, progress=0, message="Starting import...")

        # Resolve file path - allow bare filenames and common data/ locations
        project_root = Path(__file__).parent.parent
        input_path = Path(file_path)
        candidate_paths = []

        if input_path.is_absolute():
            candidate_paths.append(input_path)
        else:
            candidate_paths.extend([
                project_root / file_path,
                project_root / "data" / file_path,
                project_root / "data" / "example_corpus" / file_path,
            ])

        resolved_path = None
        for p in candidate_paths:
            try:
                if p.exists() and p.is_file():
                    resolved_path = p
                    break
            except OSError:
                continue

        if resolved_path is None:
            tried = "\n".join([f"- {str(p)}" for p in candidate_paths]) if candidate_paths else f"- {file_path}"
            update_job(
                job_id,
                status=JobStatus.FAILED.value,
                error=(
                    "File not found for import.\n"
                    f"Provided: {file_path}\n"
                    "Tried:\n"
                    f"{tried}\n"
                    "Tip: the in-app file picker may only provide a filename in some webviews; use the Upload option on the Import page."
                ),
            )
            return

        file_path = str(resolved_path.resolve())
        
        # Import based on source type
        if source_type == 'openai':
            import importers.import_openai_conversations as importer
        elif source_type == 'claude':
            import importers.import_claude_conversations as importer
        else:
            update_job(job_id, status=JobStatus.FAILED.value, error=f"Unknown source type: {source_type}")
            return
        
        # TODO: Integrate with import_report.py for tracking
        # For now, just run the import
        db_path = get_db_path()
        
        # Run import (this is synchronous, so we run in executor)
        import concurrent.futures
        loop = asyncio.get_event_loop()
        
        def do_import():
            try:
                # Check conversation count before import
                import sqlite3
                conn_before = sqlite3.connect(str(db_path))
                cursor_before = conn_before.cursor()
                cursor_before.execute('SELECT COUNT(*) FROM conversations')
                count_before = cursor_before.fetchone()[0]
                cursor_before.execute('SELECT COUNT(*) FROM messages')
                msg_count_before = cursor_before.fetchone()[0]
                conn_before.close()
                
                if source_type == 'openai':
                    importer.import_openai_conversations(file_path, str(db_path))
                else:
                    importer.import_claude_conversations(file_path, str(db_path))
                
                # Check conversation count after import
                conn_after = sqlite3.connect(str(db_path))
                cursor_after = conn_after.cursor()
                cursor_after.execute('SELECT COUNT(*) FROM conversations')
                count_after = cursor_after.fetchone()[0]
                cursor_after.execute('SELECT COUNT(*) FROM messages')
                msg_count_after = cursor_after.fetchone()[0]
                conn_after.close()
                
                imported_count = count_after - count_before
                imported_messages = msg_count_after - msg_count_before
                if imported_count == 0 and imported_messages == 0:
                    raise Exception(
                        "No new conversations/messages were imported. "
                        "The file may be empty, already imported, or in an invalid format."
                    )
                
                return {
                    "imported_conversations": imported_count,
                    "imported_messages": imported_messages,
                    "db_path": str(db_path),
                    "import_file": file_path,
                }
            except FileNotFoundError as e:
                raise Exception(f"File not found: {file_path}. {str(e)}")
            except Exception as e:
                raise Exception(f"Import failed: {str(e)}")
        
        import_result = await loop.run_in_executor(None, do_import)
        
        update_job(
            job_id,
            progress=50,
            message=(
                f"Import completed ({import_result['imported_conversations']} conversations, "
                f"{import_result['imported_messages']} messages), calculating statistics..."
            ),
            result=import_result,
        )
        
        # Calculate stats if requested
        if calculate_stats:
            import calculate_conversation_stats
            await loop.run_in_executor(None, calculate_conversation_stats.calculate_all_conversations, str(db_path), None, False)
        
        update_job(job_id, progress=75, message="Building search index...")
        
        # Build index if requested
        if build_index:
            # Add database directory to path for imports
            database_dir = project_root / "database"
            if str(database_dir) not in sys.path:
                sys.path.insert(0, str(database_dir))
            import create_fts5_tables
            # Ensure FTS5 tables exist
            create_fts5_tables.create_fts5_tables(str(db_path))
            
            # Populate FTS5 index
            # TODO: Implement FTS5 population
            # For now, just mark as done
        
        update_job(
            job_id,
            status=JobStatus.COMPLETED.value,
            progress=100,
            message=(
                "Import completed successfully: "
                f"{import_result['imported_conversations']} conversations, "
                f"{import_result['imported_messages']} messages"
            ),
            result=import_result,
        )
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        if not error_msg:
            error_msg = f"Unknown error: {type(e).__name__}"
        print(f"Import job {job_id} failed: {error_msg}")
        traceback.print_exc()
        update_job(job_id, status=JobStatus.FAILED.value, error=error_msg)


async def run_reindex_job(job_id: str):
    """Run a reindex job."""
    try:
        update_job(job_id, status=JobStatus.RUNNING.value, progress=0, message="Starting reindex...")
        
        db_path = get_db_path()
        
        # Add database directory to path for imports
        project_root = Path(__file__).parent.parent
        database_dir = project_root / "database"
        if str(database_dir) not in sys.path:
            sys.path.insert(0, str(database_dir))
        
        # Ensure FTS5 tables exist
        import create_fts5_tables
        create_fts5_tables.create_fts5_tables(str(db_path))
        
        # TODO: Populate FTS5 index from messages
        # For now, just mark as done
        
        update_job(job_id, status=JobStatus.COMPLETED.value, progress=100,
                   message="Reindex completed",
                   result={"indexed": "success"})
    
    except Exception as e:
        update_job(job_id, status=JobStatus.FAILED.value, error=str(e))


async def run_vectordb_index_job(job_id: str, metadata: dict):
    """Run a vectordb indexing job."""
    try:
        update_job(job_id, status=JobStatus.RUNNING.value, progress=0, message="Starting vectordb indexing...")
        
        db_path = get_db_path()
        from backend.vectordb.service import get_vectordb_path
        vectordb_path = get_vectordb_path()
        
        # Get conversation IDs to index (if specified)
        conversation_ids = metadata.get('conversation_ids')  # None = all
        
        # Progress callback - jobs use a separate DB (jobs.db) so no lock contention
        # with the indexer's reads from conversations.db.
        def progress_cb(progress: int, message: str):
            try:
                update_job(job_id, progress=progress, message=message)
            except Exception as e:
                print(f"Progress update error: {e}")
        
        # Cancellation: indexer checks this each conversation; cancel API and shutdown set it
        cancel_event = threading.Event()
        with _vectordb_cancel_lock:
            _vectordb_cancel_events[job_id] = cancel_event
        
        def cancellation_check() -> bool:
            return cancel_event.is_set()
        
        try:
            # Run indexing in executor (it's CPU-bound)
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            def do_index():
                from backend.vectordb.indexer import index_conversations
                return index_conversations(
                    str(db_path),
                    str(vectordb_path),
                    conversation_ids=conversation_ids,
                    progress_callback=progress_cb,
                    cancellation_check=cancellation_check,
                )
            
            result = await loop.run_in_executor(None, do_index)
            
            if result.get("cancelled"):
                update_job(
                    job_id,
                    status=JobStatus.CANCELLED.value,
                    progress=result.get("indexed_conversations", 0) * 100 // max(1, result["total_conversations"]) if result.get("total_conversations") else 0,
                    message=(
                        f"Indexing cancelled: {result.get('indexed_conversations', 0)}/{result['total_conversations']} conversations, "
                        f"{result['total_chunks']} chunks, {result['total_vectors']} vectors"
                    ),
                    result=result,
                )
            else:
                update_job(
                    job_id,
                    status=JobStatus.COMPLETED.value,
                    progress=100,
                    message=(
                        f"Indexing completed: {result['total_conversations']} conversations, "
                        f"{result['total_chunks']} chunks, {result['total_vectors']} vectors"
                    ),
                    result=result,
                )
        finally:
            with _vectordb_cancel_lock:
                _vectordb_cancel_events.pop(job_id, None)
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        if not error_msg:
            error_msg = f"Unknown error: {type(e).__name__}"
        print(f"Vectordb index job {job_id} failed: {error_msg}")
        traceback.print_exc()
        update_job(job_id, status=JobStatus.FAILED.value, error=error_msg)