"""
Pydantic models for API responses.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ConversationSummary(BaseModel):
    """Summary of a conversation for list view."""
    conversation_id: str
    title: Optional[str]
    create_time: Optional[float]
    update_time: Optional[float]
    message_count: int
    word_count: int
    ai_source: Optional[str]
    is_starred: bool = False
    tags: List[str] = []
    custom_title: Optional[str] = None


class Message(BaseModel):
    """A single message."""
    message_id: str
    role: str
    content: str
    create_time: Optional[float]
    parent_id: Optional[str] = None


class ConversationDetail(BaseModel):
    """Full conversation details."""
    conversation_id: str
    title: Optional[str]
    custom_title: Optional[str] = None
    create_time: Optional[float]
    update_time: Optional[float]
    ai_source: Optional[str]
    is_starred: bool = False
    tags: List[str] = []
    stats: Optional[Dict[str, Any]] = None


class JobStatus(BaseModel):
    """Job status for progress tracking."""
    job_id: str
    job_type: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    progress: int = 0  # 0-100
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "1.0.0"

