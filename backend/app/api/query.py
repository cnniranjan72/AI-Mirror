import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import enforce_write_match, resolve_user_id
from app.services import rag, persona as persona_svc, chat_memory, readiness
from backend.cognitive_pipeline.pipeline import get_cognitive_pipeline
from backend.cognitive_planning.intent_planner import matched_nothing
from backend.cognitive_planning.planner_models import UserIntentType
from backend.verbalizer.followups import generate_follow_ups
from app.core.rate_limit import query_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()


_INTENT_LABELS = {
    "identity_question": "Who I am",
    "behavioral_question": "What I do",
    "memory_question": "Something I saw",
    "recommendation": "What to try next",
    "explanation": "Why that is",
    "reflection": "How I have changed",
    "comparison": "Comparing two things",
    "prediction": "What I will do",
    "coaching": "Help me change",
    "information": "A plain fact",
}


# The readings a caller may ask for, in the order a person would scan them
# rather than enum order. UNKNOWN is left out: it is what the classifier says
# when it has nothing, never something a user means.
INTENT_OPTIONS = [
    {"value": t.value, "label": _INTENT_LABELS[t.value]}
    for t in UserIntentType
    if t is not UserIntentType.UNKNOWN
]


class QueryRequest(BaseModel):
    user_id: str = "default"
    query: str
    top_k: int = 5
    conversation_id: Optional[str] = None
    # How to read the question, when the caller already knows the classifier
    # got it wrong. Omitted on a first ask; sent on a re-ask.
    intent: Optional[str] = None


class SourceItem(BaseModel):
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list
    query: str
    template_used: str
    docs_retrieved: int
    trace_id: Optional[str] = None
    llm_used: bool = False
    follow_ups: list = []
    pipeline_stages: Optional[dict] = None
    pipeline_time_ms: Optional[float] = None

    # How the question was read, and how sure the classifier was. The reading
    # selects the retrieval plan, so it decides which stores the answer is
    # drawn from - and on phrasing the rules were not built from the classifier
    # is right about 56% of the time. An answer that was assembled from the
    # wrong sources should at least say which sources it thought to use.
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    # False when no pattern matched the question at all, so the reading is a
    # default rather than a conclusion. This replaces a confidence threshold
    # the client used to apply: below 0.5 fired on 56 of 65 real queries, while
    # this fires on the 11 of 36 held-out queries that are 9% correct against
    # 76% for the rest. See intent_planner.matched_nothing.
    intent_understood: bool = True
    # Present so a client can offer the alternatives without hardcoding a list
    # that would drift from the enum.
    intent_options: list = []
    # True when the reading came from the caller rather than the classifier.
    intent_overridden: bool = False

    # Why an account could not be answered about, when that is the reason.
    # None on a normal answer. Present so a client can tell an empty account
    # from a broken one - the fallback used to render both identically.
    data_state: Optional[str] = None


async def _remember(user_id: str, conversation_id: str, question: str,
                    answer: str, trace_id: Optional[str] = None) -> None:
    """Save both halves of a turn, and never fail a request over it.

    Only the successful path used to do this. Every other path - a new account
    asking its first question, an account whose pipeline broke - returned an
    answer and stored nothing, so the conversation a person had while the
    system had nothing to say vanished on reload. That is exactly the
    conversation worth keeping: it is the one that explains the empty history
    they are looking at.
    """
    if not answer:
        return
    try:
        await chat_memory.save_message(user_id, conversation_id, "user", question)
        await chat_memory.save_message(
            user_id, conversation_id, "assistant", answer, trace_id=trace_id)
    except Exception:
        logger.warning("Could not persist chat turn", exc_info=True)


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(query_rate_limit)])
async def query_insights(req: QueryRequest, authorization: Optional[str] = Header(default=None)):
    enforce_write_match(authorization, req.user_id)
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    conversation_id = req.conversation_id or f"conv_{req.user_id}"

    # Load prior turns so the character has continuity within the conversation.
    history = []
    try:
        history = await chat_memory.get_recent_turns(req.user_id, conversation_id, max_turns=6)
    except Exception:
        logger.warning("Could not load conversation history", exc_info=True)

    try:
        pipeline = get_cognitive_pipeline()
        p_result = await pipeline.process_query(
            user_id=req.user_id,
            query=req.query,
            conversation_id=conversation_id,
            conversation_history=history,
            override_intent=req.intent,
        )

        if p_result.success and p_result.verbalizer_response:
            answer = p_result.verbalizer_response.content
            # Persist this turn (user + assistant) for future continuity.
            await _remember(req.user_id, conversation_id, req.query, answer,
                            trace_id=p_result.pipeline_id)
            sources = []
            if p_result.fused_evidence:
                for fact in p_result.fused_evidence.facts[:5]:
                    sources.append({"text": fact.claim, "score": fact.confidence})
            vr = p_result.verbalizer_response
            llm_used = bool(vr and vr.success and not getattr(vr, "used_fallback", False))

            # Deterministically derived from the same context the answer was
            # built from — never invented by the LLM.
            follow_ups = []
            try:
                if p_result.character_context and p_result.character_plan:
                    follow_ups = generate_follow_ups(p_result.character_context, p_result.character_plan)
            except Exception:
                logger.warning("Follow-up generation failed", exc_info=True)

            # Report the reading that was actually used, which is the
            # override when one was honoured and the classifier's otherwise -
            # read off the plan rather than echoed back from the request, so a
            # name the pipeline rejected cannot be reported as accepted.
            intent_plan = p_result.character_plan.intent_plan if p_result.character_plan else None
            used_intent = intent_plan.intent_type.value if intent_plan else None

            return QueryResponse(
                answer=answer,
                sources=sources,
                query=req.query,
                template_used="cognitive_pipeline_v3",
                docs_retrieved=len(p_result.fused_evidence.facts) if p_result.fused_evidence else 0,
                trace_id=p_result.pipeline_id,
                llm_used=llm_used,
                follow_ups=follow_ups,
                pipeline_stages=p_result.stages,
                pipeline_time_ms=p_result.total_time_ms,
                intent=used_intent,
                intent_confidence=intent_plan.intent_confidence if intent_plan else None,
                intent_understood=not matched_nothing(intent_plan) if intent_plan else True,
                intent_options=INTENT_OPTIONS,
                intent_overridden=bool(req.intent) and req.intent == used_intent,
            )

        # The pipeline stops before planning when there is no snapshot to read
        # from, which for a new account is every question they ask. Falling
        # through to retrieval then produced "Here's what I found relevant to
        # your query: No behavioral data found yet" - a claim to have searched,
        # and a report of nothing, in one breath.
        state = await readiness.account_state(req.user_id)
        message = readiness.explain(state)
        if message:
            await _remember(req.user_id, conversation_id, req.query, message)
            return QueryResponse(
                answer=message,
                sources=[],
                query=req.query,
                template_used="account_state",
                docs_retrieved=0,
                data_state=state["state"],
            )

        logger.warning(
            "Cognitive pipeline failed for %s with a snapshot present; "
            "falling back to simple RAG", req.user_id,
        )
        persona_data = await persona_svc.get_latest_persona(req.user_id)
        result = await rag.query(
            user_id=req.user_id,
            query_text=req.query,
            top_k=req.top_k,
            persona_data=persona_data,
        )

        await _remember(req.user_id, conversation_id, req.query, result.get("answer", ""))
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


@router.get("/chat/history")
async def get_chat_history(
    user_id: str = Depends(resolve_user_id),
    conversation_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    """Persisted conversation turns for the character's continuity."""
    conv = conversation_id or f"conv_{user_id}"
    messages = await chat_memory.get_history(user_id, conv, limit=limit)
    return {"conversation_id": conv, "messages": messages}


@router.delete("/chat/history")
async def clear_chat_history(
    user_id: str = Depends(resolve_user_id),
    conversation_id: Optional[str] = Query(default=None),
):
    from app.db.postgres import execute
    conv = conversation_id or f"conv_{user_id}"
    await execute(
        "DELETE FROM chat_messages WHERE user_id = $1 AND conversation_id = $2",
        user_id, conv,
    )
    return {"success": True, "conversation_id": conv}