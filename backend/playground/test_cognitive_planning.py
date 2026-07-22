"""
Phase 5 Integration Tests — Cognitive Planning & Character RAG

Tests deterministic cognition: same question → same Character Plan → same retrieval → same reasoning → only wording changes.
Architecture V3 — FROZEN. No redesign.
"""
import asyncio
import json
import logging
import sys
import os
import time
import hashlib
from typing import List

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("test_cognitive_planning")

from cognitive_planning.planner_orchestrator import get_planner_orchestrator
from cognitive_planning.planner_models import (
    UserIntentType, ReasoningMode, ResponseStructure, CharacterPlan,
)
from rag.citation_manager import get_citation_manager
from rag.retriever import Retriever, RetrievalResult, RetrievedObject, get_retriever
from rag.memory_ranker import MemoryRanker, get_memory_ranker
from rag.fusion import FusionEngine, get_fusion_engine
from rag.context_builder import ContextBuilder, CharacterContext, get_context_builder
from verbalizer.verbalizer import LLMVerbalizer, get_verbalizer


def _create_mock_retrieval() -> RetrievalResult:
    return RetrievalResult(
        objects=[
            RetrievedObject(
                object_id="bo_001", source_type="behavior_object",
                content={
                    "topic": "machine learning",
                    "confidence_score": 0.85,
                    "stability_score": 0.7,
                    "engagement_statistics": {"overall_engagement_rate": 0.8},
                    "temporal_statistics": {"occurrence_count": 25, "recency_score": 0.9},
                    "evidence_references": ["ev_001", "ev_002"],
                },
                confidence=0.85, relevance_score=0.9, topic="machine learning",
            ),
            RetrievedObject(
                object_id="bo_002", source_type="behavior_object",
                content={
                    "topic": "python programming",
                    "confidence_score": 0.75,
                    "stability_score": 0.65,
                    "engagement_statistics": {"overall_engagement_rate": 0.7},
                    "temporal_statistics": {"occurrence_count": 18, "recency_score": 0.8},
                    "evidence_references": ["ev_003"],
                },
                confidence=0.75, relevance_score=0.8, topic="python programming",
            ),
            RetrievedObject(
                object_id="snap_001", source_type="identity_snapshot",
                content={
                    "identity_version": 5,
                    "overall_confidence": 0.72,
                    "identity_completeness": 0.65,
                    "dominant_topics": ["machine learning", "python programming", "data science"],
                    "emerging_topics": ["rust", "systems programming"],
                },
                confidence=0.72, relevance_score=0.95,
            ),
            RetrievedObject(
                object_id="sm_001", source_type="self_model",
                content={
                    "overall_confidence": 0.68,
                    "strong_beliefs": ["bel_001", "bel_002"],
                    "uncertain_beliefs": ["bel_003"],
                    "primary_motivation_belief": "bel_001",
                    "uncertainty_map": {
                        "high_uncertainty_domains": ["systems programming"],
                    },
                },
                confidence=0.68, relevance_score=0.9,
            ),
            RetrievedObject(
                object_id="ev_001", source_type="evidence",
                content={
                    "evidence_type": "behavioral",
                    "confidence": 0.8,
                    "explanation": "High engagement with ML tutorials",
                    "supporting_behavior_objects": ["bo_001"],
                },
                confidence=0.8, relevance_score=0.7,
            ),
            RetrievedObject(
                object_id="inf_001", source_type="inference",
                content={
                    "label": "learning_motivation",
                    "description": "User shows strong learning motivation in technical topics",
                    "confidence": 0.75,
                    "importance": 0.8,
                },
                confidence=0.75, relevance_score=0.85,
            ),
        ],
        total_retrieved=6,
        directives_fulfilled=3,
        directives_total=3,
    )


def test_deterministic_planning():
    """Same question → same CharacterPlan hash"""
    logger.info("=" * 60)
    logger.info("TEST: Deterministic Planning")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    query = "What are my main interests?"

    plans: List[CharacterPlan] = []
    for i in range(3):
        plan = orchestrator.build_plan(user_id="test_user", query=query)
        plans.append(plan)
        logger.info(f"  Run {i+1}: {plan.get_summary()}")

    hashes = []
    for p in plans:
        plan_str = f"{p.intent_plan.intent_type.value}|{p.reasoning_plan.primary_mode.value}|{p.response_plan.primary_structure.value}|{p.overall_confidence:.4f}"
        hashes.append(hashlib.md5(plan_str.encode()).hexdigest())

    assert hashes[0] == hashes[1] == hashes[2], (
        f"Deterministic planning FAILED: hashes differ {hashes}"
    )
    logger.info(f"  PASS: Deterministic planning produced identical plans (hash={hashes[0]})")
    logger.info("")


def test_intent_classification():
    """Test intent classification for all intent types"""
    logger.info("=" * 60)
    logger.info("TEST: Intent Classification")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    test_cases = [
        ("What is machine learning?", UserIntentType.INFORMATION),
        ("Can you recommend some good tutorials?", UserIntentType.RECOMMENDATION),
        ("Why do I keep watching Python videos?", UserIntentType.EXPLANATION),
        ("What have I been learning lately?", UserIntentType.REFLECTION),
        ("Compare my interest in AI vs programming", UserIntentType.COMPARISON),
        ("Will I continue learning Rust?", UserIntentType.PREDICTION),
        ("How can I improve my learning habits?", UserIntentType.COACHING),
        ("What kind of learner am I?", UserIntentType.IDENTITY_QUESTION),
        ("What did I watch last week?", UserIntentType.MEMORY_QUESTION),
        ("How often do I watch coding content?", UserIntentType.BEHAVIORAL_QUESTION),
    ]

    passed = 0
    for query, expected in test_cases:
        plan = orchestrator.build_plan(user_id="test_user", query=query)
        actual = plan.intent_plan.intent_type
        match = actual == expected
        status = "PASS" if match else "FAIL"
        logger.info(f"  [{status}] '{query[:50]}...' → {actual.value} (expected {expected.value})")
        if match:
            passed += 1

    logger.info(f"  Intent classification: {passed}/{len(test_cases)} passed ({passed/len(test_cases)*100:.0f}%)")
    assert passed >= 8, f"Intent classification accuracy too low: {passed}/{len(test_cases)}"
    logger.info("")


def test_communication_style_vector():
    """Test style vector computation for different intents"""
    logger.info("=" * 60)
    logger.info("TEST: Communication Style Vector")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    queries = [
        "What is deep learning?",
        "How can I improve?",
        "Who am I?",
    ]

    for query in queries:
        plan = orchestrator.build_plan(user_id="test_user", query=query)
        sv = plan.response_plan.style_vector
        logger.info(f"  '{query[:40]}...'")
        logger.info(f"    verbosity={sv.verbosity:.2f}, technical_depth={sv.technical_depth:.2f}, "
                    f"detail={sv.detail:.2f}, motivation={sv.motivation:.2f}, "
                    f"reflection={sv.reflection:.2f}")

    logger.info("  PASS: Style vector computed for all intents")
    logger.info("")


def test_retrieval_plan():
    """Test retrieval plan for different intents"""
    logger.info("=" * 60)
    logger.info("TEST: Retrieval Planning")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    query = "What are my interests?"
    plan = orchestrator.build_plan(user_id="test_user", query=query)
    rp = plan.retrieval_plan

    logger.info(f"  Retrieval directives: {len(rp.directives)}")
    for d in rp.directives:
        logger.info(f"    target={d.target.value}, priority={d.priority:.2f}, "
                    f"max={d.max_results}, required={d.required}")
    logger.info(f"  Estimated cost: {rp.estimated_cost:.1f}")
    assert len(rp.directives) > 0, "Retrieval plan should have at least 1 directive"
    assert rp.estimated_cost > 0, "Estimated cost should be positive"
    logger.info("  PASS: Retrieval plan generated")
    logger.info("")


def test_memory_ranking():
    """Test hybrid memory ranking"""
    logger.info("=" * 60)
    logger.info("TEST: Memory Ranking (Hybrid)")
    logger.info("=" * 60)

    mock_retrieval = _create_mock_retrieval()
    ranker = get_memory_ranker()
    identity_topics = ["machine learning", "python", "data science"]

    ranked = ranker.rank(
        mock_retrieval.objects,
        identity_topics=identity_topics,
    )

    logger.info(f"  Ranked {len(ranked)} objects:")
    for r in ranked:
        sub_str = ", ".join(f"{k[:4]}:{v:.2f}" for k, v in r.sub_scores.items())
        logger.info(f"    {r.retrieved.source_type}:{r.retrieved.object_id} "
                    f"score={r.rank_score:.4f} sub={{{sub_str}}}")

    assert len(ranked) == len(mock_retrieval.objects), "All objects should be ranked"
    assert ranked[0].rank_score >= ranked[-1].rank_score, "Ranking should be descending"
    logger.info("  PASS: Hybrid memory ranking works")
    logger.info("")


def test_evidence_fusion():
    """Test evidence fusion with deduplication"""
    logger.info("=" * 60)
    logger.info("TEST: Evidence Fusion")
    logger.info("=" * 60)

    citation_mgr = get_citation_manager()
    citation_mgr.clear()
    mock_retrieval = _create_mock_retrieval()
    fusor = get_fusion_engine()

    fused = fusor.fuse(mock_retrieval)
    logger.info(f"  Facts generated: {fused.facts_generated}")
    logger.info(f"  Duplicates removed: {fused.duplicates_removed}")
    logger.info(f"  Citations created: {fused.citations_created}")
    logger.info(f"  Aggregate confidence: {fused.aggregate_confidence:.2f}")
    logger.info(f"  Fusion time: {fused.fusion_time_ms:.1f}ms")

    for fact in fused.facts[:4]:
        logger.info(f"    [{fact.source_type}] {fact.claim[:80]}...")
        assert fact.citation_id, "Each fact must have a citation"

    assert fused.facts_generated > 0, "Should generate at least 1 fact"
    assert fused.aggregate_confidence > 0, "Aggregate confidence should be positive"
    logger.info("  PASS: Evidence fusion with provenance works")
    logger.info("")


def test_character_context_building():
    """Test CharacterContext construction"""
    logger.info("=" * 60)
    logger.info("TEST: CharacterContext Building")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    mock_retrieval = _create_mock_retrieval()
    citation_mgr = get_citation_manager()
    citation_mgr.clear()
    fusor = get_fusion_engine()
    builder = get_context_builder()

    plan = orchestrator.build_plan(user_id="test_user", query="What are my main interests?")
    fused = fusor.fuse(mock_retrieval)
    ctx = builder.build(
        user_id="test_user",
        retrieval_result=mock_retrieval,
        character_plan=plan,
        fused_evidence=fused,
    )

    logger.info(f"  Context ID: {ctx.context_id}")
    logger.info(f"  Behavior objects: {len(ctx.behavior_objects)}")
    logger.info(f"  Evidence: {len(ctx.evidence)}")
    logger.info(f"  Inferences: {len(ctx.inferences)}")
    logger.info(f"  Dominant topics: {ctx.dominant_topics}")
    logger.info(f"  Confidence: {ctx.overall_confidence:.2f}")
    logger.info(f"  Citations: {ctx.citation_count}")
    logger.info(f"  Build time: {ctx.build_time_ms:.1f}ms")

    assert ctx.character_plan is not None, "CharacterPlan should be present"
    assert ctx.overall_confidence > 0, "Confidence should be positive"
    assert len(ctx.behavior_objects) > 0, "Should have behavior objects"
    assert len(ctx.dominant_topics) > 0, "Should have dominant topics"
    logger.info("  PASS: CharacterContext built correctly")
    logger.info("")


def test_deterministic_retrieval():
    """Same query → same retrieval directives"""
    logger.info("=" * 60)
    logger.info("TEST: Deterministic Retrieval")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    query = "What am I learning?"

    plans = [orchestrator.build_plan(user_id="test_user", query=query) for _ in range(3)]
    directive_sets = []
    for p in plans:
        targets = [d.target.value for d in p.retrieval_plan.directives]
        directive_sets.append(tuple(targets))

    assert directive_sets[0] == directive_sets[1] == directive_sets[2], (
        f"Retrieval not deterministic: {directive_sets}"
    )
    logger.info(f"  Same retrieval directives across 3 runs: {directive_sets[0]}")
    logger.info("  PASS: Deterministic retrieval planning")
    logger.info("")


def test_fallback_verbalization():
    """Test verbalizer without LLM"""
    logger.info("=" * 60)
    logger.info("TEST: Fallback Verbalization")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    mock_retrieval = _create_mock_retrieval()
    citation_mgr = get_citation_manager()
    citation_mgr.clear()
    fusor = get_fusion_engine()
    builder = get_context_builder()
    verbalizer = get_verbalizer()

    plan = orchestrator.build_plan(user_id="test_user", query="What kind of learner am I?")
    fused = fusor.fuse(mock_retrieval)
    ctx = builder.build(
        user_id="test_user",
        retrieval_result=mock_retrieval,
        character_plan=plan,
        fused_evidence=fused,
    )

    result = asyncio.run(verbalizer.verbalize(ctx, plan))
    logger.info(f"  Verbalization time: {result.verbalization_time_ms:.1f}ms")
    logger.info(f"  Token count: {result.token_count}")
    logger.info(f"  Content preview: {result.content[:200]}...")

    assert result.success, "Verbalization should succeed"
    assert result.content, "Should produce content"
    logger.info("  PASS: Fallback verbalization works")
    logger.info("")


def test_risk_flags():
    """Test risk flag computation"""
    logger.info("=" * 60)
    logger.info("TEST: Risk Flags")
    logger.info("=" * 60)

    orchestrator = get_planner_orchestrator()
    plan = orchestrator.build_plan(user_id="test_user", query="")
    logger.info(f"  Empty query flags: {plan.risk_flags}")

    plan2 = orchestrator.build_plan(user_id="test_user", query="What if I change my interests?")
    logger.info(f"  Ambiguous query flags: {plan2.risk_flags}")

    assert isinstance(plan.risk_flags, list), "Risk flags should be a list"
    logger.info("  PASS: Risk flags computed")
    logger.info("")


def run_all():
    start = time.time()
    tests = [
        test_deterministic_planning,
        test_intent_classification,
        test_communication_style_vector,
        test_retrieval_plan,
        test_deterministic_retrieval,
        test_memory_ranking,
        test_evidence_fusion,
        test_character_context_building,
        test_fallback_verbalization,
        test_risk_flags,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            logger.error(f"  TEST FAILED: {test.__name__}: {e}", exc_info=True)
            failed += 1

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info(f"RESULTS: {passed}/{len(tests)} passed ({failed} failed) in {elapsed:.2f}s")
    logger.info("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
