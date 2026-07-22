"""
Deterministic cognitive-core smoke test.

Exercises the full deterministic reasoning chain end-to-end:

    planner -> retriever -> ranker -> fusion -> decision -> context -> verbalizer

on synthetic in-memory data, with NO external services — no PostgreSQL, no LLM
API, no torch / sentence-transformers. This is the fast regression guard proving
the "intelligence" (the deterministic architecture, not the LLM) is wired
correctly and produces an identity-grounded response.

Run standalone:
    python backend/tests/test_cognitive_core_smoke.py
Or via pytest:
    pytest backend/tests/test_cognitive_core_smoke.py
"""
import asyncio
import os
import sys

# The cognitive modules import each other via the `backend.` package prefix, so
# both the project root and the backend dir must be importable. Set a dummy
# DATABASE_URL so any transitively-imported db module does not raise at import.
os.environ.setdefault("DATABASE_URL", "postgres://smoke-test-dummy")
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
for _p in (_PROJECT_ROOT, _BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.cognitive_planning.planner_orchestrator import get_planner_orchestrator
from backend.rag.retriever import get_retriever
from backend.rag.memory_ranker import get_memory_ranker
from backend.rag.fusion import get_fusion_engine
from backend.rag.context_builder import get_context_builder
from backend.cognitive_pipeline.decision_engine import get_decision_engine
from backend.verbalizer.verbalizer import LLMVerbalizer


def _synthetic_context():
    """A minimal but realistic retrieval context, matching the dict shapes the
    pipeline loads from PostgreSQL in `_load_retrieval_context`."""
    return {
        "identity_snapshot": {
            "snapshot_id": "snap_1", "identity_id": "id_1", "user_id": "u1",
            "identity_version": 3, "overall_confidence": 0.71,
            "identity_completeness": 0.64,
            "dominant_topics": ["fitness", "cooking", "technology"],
            "emerging_topics": ["photography"],
            "personality_traits": {"openness": 0.7},
        },
        "self_model": {
            "self_model_id": "sm_1", "overall_confidence": 0.68,
            "beliefs": [{"claim": "enjoys learning", "confidence": 0.8}],
            "strong_beliefs": [{"claim": "values fitness", "confidence": 0.85}],
            "uncertain_beliefs": [{"claim": "may prefer mornings", "confidence": 0.4}],
            "primary_motivation_belief": "self-improvement",
        },
        "behavior_objects": [
            {"unique_id": "bo_1", "topic": "fitness", "confidence_score": 0.82,
             "engagement_statistics": {"overall_engagement_rate": 0.6},
             "temporal_statistics": {"occurrence_count": 42},
             "creators": ["athlete_a"], "confidence": 0.82},
            {"unique_id": "bo_2", "topic": "cooking", "confidence_score": 0.74,
             "engagement_statistics": {"overall_engagement_rate": 0.5},
             "temporal_statistics": {"occurrence_count": 30},
             "creators": ["chef_b"], "confidence": 0.74},
        ],
        "evidence": [
            {"evidence_id": "ev_1", "evidence_type": "engagement", "topic": "fitness",
             "claim": "Consistently watches fitness reels to completion",
             "confidence": 0.8, "supporting_behavior_objects": ["bo_1"]},
            {"evidence_id": "ev_2", "evidence_type": "temporal", "topic": "cooking",
             "claim": "Evening cooking content engagement",
             "confidence": 0.66, "supporting_behavior_objects": ["bo_2"]},
        ],
        "inferences": [
            {"inference_id": "inf_1", "label": "health_conscious",
             "description": "Strong recurring interest in fitness and wellness",
             "confidence": 0.78, "affected_topics": ["fitness"]},
        ],
    }


def run_core(query: str = "What are my main interests, and how confident are you?",
             user_id: str = "u1", verbose: bool = False):
    """Drive the deterministic chain once and return the verbalizer response."""
    planner = get_planner_orchestrator()
    plan = planner.build_plan(user_id=user_id, query=query)

    ctx = _synthetic_context()

    retriever = get_retriever()
    # Ensure the in-memory context path is used (no DB loaders registered).
    retriever._data_sources.clear()
    rr = retriever.retrieve(plan=plan.retrieval_plan, context=ctx)

    ranked = get_memory_ranker().rank(
        objects=rr.objects,
        identity_topics=ctx["identity_snapshot"]["dominant_topics"],
        goal_ids=[],
    )

    fused = get_fusion_engine().fuse(retrieval_result=rr, ranked_objects=ranked)

    final_ctx = get_decision_engine().decide(
        fused_evidence=fused, character_plan=plan,
        retrieval_result=rr, ranked_objects=ranked, retrieval_context=ctx,
    )

    char_ctx = get_context_builder().build(
        user_id=user_id,
        retrieval_result=final_ctx.filtered_retrieval_result,
        character_plan=plan, fused_evidence=fused,
        identity_snapshot=ctx["identity_snapshot"], self_model=ctx["self_model"],
    )

    # llm_call=None exercises the deterministic verbalization path (no API key).
    vresp = asyncio.run(LLMVerbalizer(llm_call=None).verbalize(context=char_ctx, plan=plan))

    if verbose:
        print("plan     :", plan.get_summary())
        print(f"retrieve : {rr.total_retrieved} objects "
              f"({rr.directives_fulfilled}/{rr.directives_total} directives)")
        print(f"rank     : {len(ranked)} ranked")
        print(f"fuse     : {fused.facts_generated} facts, agg_conf={fused.aggregate_confidence:.2f}")
        print(f"decide   : {final_ctx.metrics.input_facts} -> {final_ctx.metrics.final_facts} facts")
        print(f"context  : {char_ctx.get_summary()}")
        print(f"verbalize: success={vresp.success} len={len(vresp.content)}")
        print("-" * 60)
        print(vresp.content)
        print("-" * 60)

    return plan, vresp


def test_cognitive_core_end_to_end():
    plan, vresp = run_core()
    assert plan.intent_plan.intent_type.value == "identity_question"
    assert vresp.success, "verbalizer reported failure"
    assert vresp.content.strip(), "verbalizer produced empty content"


if __name__ == "__main__":
    _, resp = run_core(verbose=True)
    assert resp.success and resp.content.strip()
    print("SMOKE TEST PASSED")
