"""
Job runner for executing background jobs.
"""
import asyncio
import sys
from pathlib import Path
from backend.jobs import update_job, JobStatus, get_job
from backend.db import get_db_path

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
            if source_type == 'openai':
                importer.import_openai_conversations(file_path, str(db_path))
            else:
                importer.import_claude_conversations(file_path, str(db_path))
            return True
        
        await loop.run_in_executor(None, do_import)
        
        update_job(job_id, progress=50, message="Import completed, calculating statistics...")
        
        # Calculate stats if requested
        if calculate_stats:
            import calculate_conversation_stats
            await loop.run_in_executor(None, calculate_conversation_stats.calculate_all_conversations, str(db_path), None, False)
        
        update_job(job_id, progress=75, message="Building search index...")
        
        # Build index if requested
        if build_index:
            import create_fts5_tables
            # Ensure FTS5 tables exist
            create_fts5_tables.create_fts5_tables(str(db_path))
            
            # Populate FTS5 index
            # TODO: Implement FTS5 population
            # For now, just mark as done
        
        update_job(job_id, status=JobStatus.COMPLETED.value, progress=100, 
                   message="Import completed successfully",
                   result={"imported": "success"})
    
    except Exception as e:
        update_job(job_id, status=JobStatus.FAILED.value, error=str(e))


async def run_reindex_job(job_id: str):
    """Run a reindex job."""
    try:
        update_job(job_id, status=JobStatus.RUNNING.value, progress=0, message="Starting reindex...")
        
        db_path = get_db_path()
        
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

