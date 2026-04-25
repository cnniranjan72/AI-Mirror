"""
POST /query — RAG-powered behavioral insights
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import rag, persona as persona_svc

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    user_id: str = "default"
    query: str
    top_k: int = 5


class SourceItem(BaseModel):
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list
    query: str
    template_used: str
    docs_retrieved: int


@router.post("/query", response_model=QueryResponse)
async def query_insights(req: QueryRequest):
    """
    RAG query pipeline:
    1. Embed query
    2. Retrieve top-k documents (hybrid search)
    3. Generate template-based response with persona context
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Get persona context
        persona_data = await persona_svc.get_latest_persona(req.user_id)

        # Run RAG
        result = await rag.query(
            user_id=req.user_id,
            query_text=req.query,
            top_k=req.top_k,
            persona_data=persona_data,
        )

        logger.info("Query served user=%s docs=%d", req.user_id, result["docs_retrieved"])
        return QueryResponse(**result)

    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(e))
