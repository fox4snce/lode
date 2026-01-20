from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.vectordb import service as vectordb_service


router = APIRouter(prefix="/api/vectordb", tags=["vectordb"])


class VectorSearchRequest(BaseModel):
    phrases: List[str] = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    min_similarity: Optional[float] = Field(None, ge=-1.0, le=1.0)
    filters: Optional[Dict[str, Any]] = None
    include_content: bool = True
    include_debug: bool = False


@router.post("/search")
def vectordb_search(req: VectorSearchRequest):
    try:
        results_by_phrase = vectordb_service.search_phrases(
            phrases=req.phrases,
            top_k=req.top_k,
            min_similarity=req.min_similarity,
            filters=req.filters,
            include_content=req.include_content,
            include_debug=req.include_debug,
        )
        return {"results_by_phrase": results_by_phrase}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def vectordb_status():
    try:
        return vectordb_service.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

