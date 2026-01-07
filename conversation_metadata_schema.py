"""
Pydantic schema for conversation metadata extraction.
This defines the structured output format for LLM-generated metadata.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Evidence(BaseModel):
    """Evidence pointing to a specific message in the conversation."""
    message_id: str = Field(..., description="The message ID where this evidence comes from")
    excerpt: Optional[str] = Field(None, max_length=200, description="Short excerpt (max 200 chars)")


class ProjectCandidate(BaseModel):
    """A project discovered in the conversation."""
    name: str = Field(..., max_length=100, description="Project name")
    description: str = Field(..., max_length=300, description="Short description")
    # Evidence intentionally disabled to keep metadata compact (force empty list)
    evidence: List[Evidence] = Field(..., max_items=0, description="Unused. Always []")


class Entity(BaseModel):
    """An entity (person, place, tool, company, etc.) mentioned in the conversation."""
    name: str = Field(..., max_length=100, description="Entity name")
    entity_type: str = Field(..., max_length=50, description="Type: person, place, tool, company, character, world, etc.")
    # Evidence intentionally disabled to keep metadata compact (force empty list)
    evidence: List[Evidence] = Field(..., max_items=0, description="Unused. Always []")


class ConversationMetadata(BaseModel):
    """Complete metadata for a conversation."""
    
    # Basic summarization
    title: str = Field(..., max_length=120, description="Short title for the conversation")
    summary: str = Field(..., max_length=800, description="Compact one-paragraph summary")
    one_liner: Optional[str] = Field(None, max_length=120, description="One-line summary (index-card style)")
    
    # Classification
    conversation_types: List[str] = Field(..., max_items=5, description="Types: planning, problem-solving, coding, writing, research, etc.")
    intents: List[str] = Field(..., max_items=5, description="User intents: learn, build, debug, explore, document, etc.")
    status: str = Field(..., description="Status: resolved, ongoing, abandoned, unclear")
    classification_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1 for classification")
    
    # Topics and keywords
    topics: List[str] = Field(..., max_items=8, description="Normalized topic strings (most important only)")
    keywords: List[str] = Field(..., max_items=12, description="Keywords for lexical search (most relevant only)")
    
    # Projects and entities
    project_candidates: List[ProjectCandidate] = Field(default_factory=list, max_items=5, description="Discovered projects (only if clearly discussed)")
    # NOTE: intentionally omitting entities/relationships/outputs/open_loops/quotes to keep metadata compact.
    
    # Metadata about the metadata
    schema_version: str = Field(default="1.0", description="Schema version")
    model_used: Optional[str] = Field(None, description="Model used for extraction")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score 0-1")


