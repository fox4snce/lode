"""
Job API routes for long-running tasks.
"""
from fastapi import APIRouter, Path as PathParam, HTTPException, BackgroundTasks
from typing import Dict, Any, List
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models import JobStatus
from backend.jobs import create_job, get_job, list_jobs, cancel_job, JobType, JobStatus as JobStatusEnum
import uuid
import asyncio

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/import", response_model=Dict[str, str])
async def create_import_job(background_tasks: BackgroundTasks):
    """Create an import job."""
    # This endpoint is handled by backend/main.py
    # Keep this for compatibility but it shouldn't be called
    raise HTTPException(status_code=404, detail="Use POST /api/jobs/import from main router")


@router.post("/reindex", response_model=Dict[str, str])
async def create_reindex_job(background_tasks: BackgroundTasks):
    """Create a reindex job."""
    # This endpoint is handled by backend/main.py
    raise HTTPException(status_code=404, detail="Use POST /api/jobs/reindex from main router")


@router.get("/", response_model=List[JobStatus])
async def list_jobs_endpoint():
    """List all jobs."""
    jobs_list = list_jobs()
    return [JobStatus(**job) for job in jobs_list]


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_endpoint(job_id: str = PathParam(..., description="Job ID")):
    """Get job status."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(**job)


@router.post("/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str = PathParam(..., description="Job ID")):
    """Cancel a job."""
    if cancel_job(job_id):
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Job not found")

