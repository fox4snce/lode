"""
Job system with SQLite persistence.
"""
import sqlite3
import uuid
import json
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum
from backend.db import get_db_connection


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    IMPORT = "import"
    REINDEX = "reindex"
    EXPORT = "export"
    CALCULATE_STATS = "calculate_stats"


def init_jobs_table():
    """Create jobs table if it doesn't exist."""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            cancelled_at TIMESTAMP,
            result_json TEXT,
            error_text TEXT,
            metadata_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def create_job(job_type: str, metadata: Optional[Dict] = None) -> str:
    """Create a new job and return job ID."""
    init_jobs_table()
    
    job_id = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO jobs (id, job_type, status, metadata_json)
        VALUES (?, ?, ?, ?)
    """, (job_id, job_type, JobStatus.PENDING.value, json.dumps(metadata) if metadata else None))
    conn.commit()
    conn.close()
    
    return job_id


def update_job(job_id: str, status: Optional[str] = None, progress: Optional[int] = None,
                message: Optional[str] = None, result: Optional[Dict] = None,
                error: Optional[str] = None):
    """Update job status."""
    conn = get_db_connection()
    
    updates = []
    params = []
    
    if status:
        updates.append("status = ?")
        params.append(status)
        if status == JobStatus.RUNNING.value:
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value):
            updates.append("completed_at = CURRENT_TIMESTAMP")
            if status == JobStatus.CANCELLED.value:
                updates.append("cancelled_at = CURRENT_TIMESTAMP")
    
    if progress is not None:
        updates.append("progress = ?")
        params.append(progress)
    
    if message:
        updates.append("message = ?")
        params.append(message)
    
    if result:
        updates.append("result_json = ?")
        params.append(json.dumps(result))
    
    if error:
        updates.append("error_text = ?")
        params.append(error)
    
    if updates:
        params.append(job_id)
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
    
    conn.close()


def get_job(job_id: str) -> Optional[Dict]:
    """Get job by ID."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    job = dict(row)
    if job.get('result_json'):
        job['result'] = json.loads(job['result_json'])
    if job.get('metadata_json'):
        job['metadata'] = json.loads(job['metadata_json'])
    
    return job


def list_jobs(limit: int = 50) -> List[Dict]:
    """List recent jobs."""
    init_jobs_table()
    conn = get_db_connection()
    cursor = conn.execute("""
        SELECT * FROM jobs
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    
    jobs = []
    for row in cursor.fetchall():
        job = dict(row)
        if job.get('result_json'):
            job['result'] = json.loads(job['result_json'])
        if job.get('metadata_json'):
            job['metadata'] = json.loads(job['metadata_json'])
        jobs.append(job)
    
    conn.close()
    return jobs


def cancel_job(job_id: str) -> bool:
    """Cancel a job if it's still pending or running."""
    job = get_job(job_id)
    if not job:
        return False
    
    if job['status'] in (JobStatus.PENDING.value, JobStatus.RUNNING.value):
        update_job(job_id, status=JobStatus.CANCELLED.value, message="Cancelled by user")
        return True
    
    return False

