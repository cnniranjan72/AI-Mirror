import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import rag, persona as persona_svc
from backend.cognitive_pipeline.pipeline import get_cognitive_pipeline

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
    pipeline_stages: Optional[dict] = None
    pipeline_time_ms: Optional[float] = None


@router.post("/query", response_model=QueryResponse)
async def query_insights(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        pipeline = get_cognitive_pipeline()
        p_result = await pipeline.process_query(
            user_id=req.user_id,
            query=req.query,
        )

        if p_result.success and p_result.verbalizer_response:
            answer = p_result.verbalizer_response.content
            sources = []
            if p_result.fused_evidence:
                for fact in p_result.fused_evidence.facts[:5]:
                    sources.append({"text": fact.claim, "score": fact.confidence})
            return QueryResponse(
                answer=answer,
                sources=sources,
                query=req.query,
                template_used="cognitive_pipeline_v3",
                docs_retrieved=len(p_result.fused_evidence.facts) if p_result.fused_evidence else 0,
                pipeline_stages=p_result.stages,
                pipeline_time_ms=p_result.total_time_ms,
            )

        logger.warning("Cognitive pipeline failed, falling back to simple RAG")
        persona_data = await persona_svc.get_latest_persona(req.user_id)
        result = await rag.query(
            user_id=req.user_id,
            query_text=req.query,
            top_k=req.top_k,
            persona_data=persona_data,
        )

        return QueryResponse(**result)

    except Exception as e:
        logger.exception("Query failed, falling back to simple RAG")
        try:
            persona_data = await persona_svc.get_latest_persona(req.user_id)
            result = await rag.query(
                user_id=req.user_id,
                query_text=req.query,
                top_k=req.top_k,
                persona_data=persona_data,
            )
            return QueryResponse(**result)
        except Exception as e2:
            logger.exception("Fallback query also failed")
            raise HTTPException(status_code=500, detail=str(e2))