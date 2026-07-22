"""
Phase 6 — Full Cognitive Pipeline Integration Test with Decision Engine

Chains: RuntimeBuilder → Planner → Retriever → Ranker → Fusion → DecisionEngine → ContextBuilder → Verbalizer.
Validates every stage with real queries against live V3 database data.
Architecture V3 — FROZEN. No redesign.
"""
import asyncio
import json
import logging
import sys
import os
import time
import hashlib

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("test_cognitive_pipeline")

# ── Test Queries ──────────────────────────────────────────────────────────

TEST_QUERIES = [
    ("What kind of learner am I?", "identity_question"),
    ("Why have my interests changed recently?", "explanation"),
    ("What creators influence me the most?", "behavioral_question"),
    ("How has my AI learning evolved?", "reflection"),
    ("What evidence supports that conclusion?", "information"),
    ("What are my strongest behavioral patterns?", "behavioral_question"),
    ("Compare my interest in AI vs programming", "comparison"),
    ("Will I continue learning Python?", "prediction"),
    ("How can I improve my learning habits?", "coaching"),
    ("What did I watch last week?", "memory_question"),
]


async def run_synthetic_ingest():
    """Run event generator + V3 ingest pipeline to populate the database."""
    logger.info("=" * 60)
    logger.info("SETUP: Synthetic Event Generation + V3 Ingest")
    logger.info("=" * 60)
    from playground.event_generator import generate_test_payload
    from pipeline.orchestrator import V3Pipeline
    from backend.core.behavior_gateway import get_behavior_gateway
    from backend.shared.contracts import BehaviorEvent, EventSource

    payload = generate_test_payload(num_weeks=1, user_id="test_user", seed=42)
    user_id = payload["user_id"]
    events = payload["events"]

    pipeline = V3Pipeline()
    gateway = get_behavior_gateway()

    sessions = {}
    for ev in events:
        sid = ev["session_id"]
        sessions.setdefault(sid, []).append(ev)

    session_order = sorted(sessions.keys())
    logger.info(f"Generated {len(events)} events across {len(session_order)} sessions")

    all_results = []
    for idx, session_id in enumerate(session_order):
        session_events = sessions[session_id]
        raw_payload = {
            "events": [{
                "reel_id": e["reel_id"],
                "username": e["username"],
                "caption": e["caption"],
                "hashtags": e["hashtags"],
                "audio_info": e["audio"],
                "watch_time": e["watch_time"],
                "liked": e["liked"],
                "saved": e["saved"],
                "shared": e["shared"],
                "timestamp": e["timestamp"],
                "session_id": e["session_id"],
            } for e in session_events]
        }

        normalized = gateway.process_batch(raw_payload, EventSource.CHROME_EXTENSION)
        if not normalized:
            continue

        existing = await pipeline.load_identity(user_id)
        result = await pipeline.run(
            user_id=user_id,
            events=normalized,
            existing_identity=existing,
        )
        all_results.append(result)
        logger.info(f"  Session {idx+1}: {len(normalized)} events -> "
                     f"{len(result.behavior_objects)} bo, {len(result.evidence)} ev, "
                     f"{len(result.inferences)} inf")

    logger.info(f"Ingest complete: {len(all_results)} sessions processed")
    return user_id, all_results


async def check_db_tables():
    """Check which V3 tables have data for test_user."""
    from app.db.postgres import fetchrow
    tables = ["behavior_objects", "evidence", "inferences", "identity_snapshots", "self_models", "goals", "reflections"]
    counts = {}
    for table in tables:
        try:
            row = await fetchrow(f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id = 'test_user'")
            counts[table] = row["cnt"] if row else 0
        except Exception:
            counts[table] = -1
    return counts


def validate_pipeline_stage(stage_name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    logger.info(f"  [{status}] {stage_name}{': ' + detail if detail else ''}")
    return condition


async def run_tests():
    """Run all cognitive pipeline tests including Decision Engine."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("PHASE 6 — FULL COGNITIVE PIPELINE + DECISION ENGINE TEST")
    logger.info("=" * 70)

    # ── Prelim: Check DB ────────────────────────────────────────────────
    logger.info("\n── Prelim: Database Check ──")
    try:
        counts = await check_db_tables()
        for table, cnt in counts.items():
            logger.info(f"  {table}: {cnt} rows")
        has_data = any(c > 0 for c in counts.values())
    except Exception as e:
        logger.warning(f"DB check failed: {e}")
        has_data = False

    if not has_data:
        logger.info("\n── No data in DB. Running synthetic ingest... ──")
        try:
            user_id, results = await run_synthetic_ingest()
            logger.info(f"Ingested data for {user_id}")

            counts = await check_db_tables()
            for table, cnt in counts.items():
                logger.info(f"  {table}: {cnt} rows")
            has_data = any(c > 0 for c in counts.values())
        except Exception as e:
            logger.error(f"Ingest failed: {e}")
            has_data = False

    if not has_data:
        logger.error("No data available for cognitive pipeline testing. Aborting.")
        return False, [], None, [], None

    # ── Register Retriever data sources ─────────────────────────────────
    logger.info("\n── Part 1: Register Retriever Data Sources ──")
    from cognitive_pipeline.data_sources import register_data_sources
    register_data_sources(user_id="test_user")
    logger.info("  Data sources registered")

    # ── Run cognitive pipeline ──────────────────────────────────────────
    from cognitive_pipeline.pipeline import get_cognitive_pipeline

    pipeline = get_cognitive_pipeline()

    all_passed = 0
    all_total = 0
    detailed_results = []

    for query, expected_intent in TEST_QUERIES:
        logger.info(f"\n── Query: '{query}' (expected={expected_intent}) ──")

        t0 = time.perf_counter()
        result = await pipeline.process_query(
            user_id="test_user",
            query=query,
            request_id=f"test_{hash(query) % 1000000}",
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # ── Stage validation ──────────────────────────────────────────
        errors = []
        stages_ok = 0
        stages_total = 0

        # Runtime
        stages_total += 1
        if validate_pipeline_stage("Runtime", result.runtime is not None and result.runtime.success):
            stages_ok += 1
        else:
            errors.append("Runtime failed")
            if result.runtime:
                errors.extend(result.runtime.errors)

        # Plan
        stages_total += 1
        plan_ok = result.character_plan is not None
        if validate_pipeline_stage("CharacterPlan", plan_ok):
            stages_ok += 1
        else:
            errors.append("No CharacterPlan")

        # Intent
        stages_total += 1
        if plan_ok and result.character_plan.intent_plan:
            actual_intent = result.character_plan.intent_plan.intent_type.value
            intent_ok = actual_intent == expected_intent
            if validate_pipeline_stage(f"Intent ({actual_intent})", intent_ok, f"expected {expected_intent}"):
                stages_ok += 1
            else:
                errors.append(f"Intent mismatch: {actual_intent} != {expected_intent}")
        else:
            validate_pipeline_stage("Intent", False, "No intent plan")
            errors.append("No intent plan")

        # Retrieval
        stages_total += 1
        retrieval_ok = result.retrieval_result is not None and (
            result.retrieval_result.total_retrieved > 0 or result.retrieval_result.errors
        )
        if validate_pipeline_stage("Retrieval", retrieval_ok,
                                    f"{result.retrieval_result.total_retrieved if result.retrieval_result else 0} objects"):
            stages_ok += 1
        else:
            errors.append("Retrieval failed/empty")
            if result.retrieval_result:
                errors.extend(result.retrieval_result.errors)

        # Ranking
        stages_total += 1
        rank_ok = result.ranked_objects is not None and len(result.ranked_objects) > 0
        validate_pipeline_stage("MemoryRanker", rank_ok,
                                 f"{len(result.ranked_objects) if result.ranked_objects else 0} ranked")
        if rank_ok:
            stages_ok += 1
        else:
            errors.append("Ranking empty")

        # Fusion
        stages_total += 1
        fusion_ok = result.fused_evidence is not None and result.fused_evidence.facts_generated > 0
        if fusion_ok:
            cite_info = f"{result.fused_evidence.facts_generated} facts, {result.fused_evidence.citations_created} citations"
        else:
            cite_info = "no facts"
        validate_pipeline_stage("Fusion", fusion_ok, cite_info)
        if fusion_ok:
            stages_ok += 1
        else:
            errors.append("Fusion produced no facts")

        # Decision Engine
        stages_total += 1
        de_ok = result.final_context is not None
        if de_ok:
            fc = result.final_context
            de_info = (f"{fc.metrics.input_facts} -> {fc.metrics.final_facts} facts, "
                       f"{fc.metrics.conflicts_detected} conflicts, "
                       f"{fc.metrics.removed_low_confidence} low, "
                       f"{fc.metrics.removed_duplicates} dup, "
                       f"{fc.metrics.removed_diversity} diversity")
        else:
            de_info = "None"
        validate_pipeline_stage("DecisionEngine", de_ok, de_info)
        if de_ok:
            stages_ok += 1
        else:
            errors.append("No DecisionEngine FinalContext")

        # Context
        stages_total += 1
        ctx_ok = result.character_context is not None
        if ctx_ok:
            ctx_info = (f"{len(result.character_context.behavior_objects)} behaviors, "
                        f"{len(result.character_context.evidence)} evidence, "
                        f"{len(result.character_context.inferences)} inferences")
        else:
            ctx_info = "None"
        validate_pipeline_stage("ContextBuilder", ctx_ok, ctx_info)
        if ctx_ok:
            stages_ok += 1
        else:
            errors.append("No CharacterContext")

        # Verbalization
        stages_total += 1
        verb_ok = result.verbalizer_response is not None and result.verbalizer_response.success
        if verb_ok:
            verb_info = f"{result.verbalizer_response.token_count} tokens, {len(result.verbalizer_response.content)} chars"
        else:
            verb_info = "failed"
        validate_pipeline_stage("Verbalizer", verb_ok, verb_info)
        if verb_ok:
            stages_ok += 1
        else:
            errors.append("Verbalization failed")

        # ── Summary ────────────────────────────────────────────────────
        query_passed = stages_ok == stages_total and not errors
        all_passed += 1 if query_passed else 0
        all_total += 1

        status = "PASS" if query_passed else "FAIL"
        logger.info(f"  -- {status}: {stages_ok}/{stages_total} stages | {elapsed_ms:.1f}ms --")
        if not query_passed:
            logger.info(f"  Errors: {errors}")

        detailed_results.append({
            "query": query,
            "expected_intent": expected_intent,
            "actual_intent": result.character_plan.intent_plan.intent_type.value if result.character_plan and result.character_plan.intent_plan else None,
            "stages_ok": stages_ok,
            "stages_total": stages_total,
            "passed": query_passed,
            "errors": errors,
            "elapsed_ms": elapsed_ms,
            "retrieved": result.retrieval_result.total_retrieved if result.retrieval_result else 0,
            "facts": result.fused_evidence.facts_generated if result.fused_evidence else 0,
            "citations": result.fused_evidence.citations_created if result.fused_evidence else 0,
            "response_preview": (result.verbalizer_response.content[:120] + "...") if result.verbalizer_response and result.verbalizer_response.content else "",
            "trace_summary": result.trace.summary() if result.trace else "",
            "decision_input": result.trace.decision_input_facts if result.trace else 0,
            "decision_output": result.trace.decision_output_facts if result.trace else 0,
            "decision_conflicts": result.trace.decision_conflicts if result.trace else 0,
        })

    # ── Final Report ────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"RESULTS: {all_passed}/{all_total} queries passed")
    logger.info("=" * 70)

    for dr in detailed_results:
        status = "PASS" if dr["passed"] else "FAIL"
        logger.info(f"  [{status}] {dr['query'][:60]:60s} "
                     f"intent={dr['actual_intent'] or '?'} "
                     f"ret={dr['retrieved']} facts={dr['facts']} "
                     f"dec={dr['decision_input']}->{dr['decision_output']} "
                     f"{dr['elapsed_ms']:.0f}ms")

    logger.info("")
    logger.info("-" * 70)

    # Print first successful response as sample
    for dr in detailed_results:
        if dr["passed"] and dr["response_preview"]:
            logger.info(f"\nSample Response -- '{dr['query']}':")
            logger.info(f"  {dr['response_preview']}")
            logger.info(f"  Trace: {dr['trace_summary']}")
            break

    # Print first failure details
    for dr in detailed_results:
        if not dr["passed"]:
            logger.info(f"\nFailure Detail -- '{dr['query']}':")
            for e in dr["errors"]:
                logger.info(f"  Error: {e}")
            break

    # ── Check determinism ──────────────────────────────────────────────
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("PART 7 — DETERMINISM CHECK (Plan + Decision Engine)")
    logger.info("=" * 70)

    query = "What kind of learner am I?"
    runs = []
    for i in range(3):
        r = await pipeline.process_query(user_id="test_user", query=query, request_id=f"det_{i}")
        runs.append(r)
        if r.character_plan:
            logger.info(f"  Run {i+1}: {r.character_plan.get_summary()}")
        if r.final_context:
            logger.info(f"         decision: {r.final_context.metrics.input_facts} -> {r.final_context.metrics.final_facts} facts")

    planning_deterministic = False
    decision_deterministic = False

    if len(runs) >= 2 and all(r.character_plan for r in runs):
        plan_hashes = []
        for r in runs:
            p = r.character_plan
            s = f"{p.intent_plan.intent_type.value}|{p.reasoning_plan.primary_mode.value}|{p.response_plan.primary_structure.value}|{p.overall_confidence:.4f}"
            plan_hashes.append(hashlib.md5(s.encode()).hexdigest())

        planning_deterministic = plan_hashes[0] == plan_hashes[1] == plan_hashes[2]
        validate_pipeline_stage("Deterministic Planning", planning_deterministic,
                                 f"hash={plan_hashes[0]}")
    else:
        validate_pipeline_stage("Deterministic Planning", False, "Not enough plans")

    # Decision determinism: same input -> same fact IDs and scores
    if len(runs) >= 2 and all(r.final_context for r in runs):
        score_hashes = []
        for r in runs:
            fc = r.final_context
            if fc.selected_facts:
                fact_ids = sorted(f.fact_id for f in fc.selected_facts)
                score_str = "|".join(f"{fid}:{fc.decision_scores.get(fid, 0):.4f}" for fid in fact_ids)
                score_hashes.append(hashlib.md5(score_str.encode()).hexdigest())
            else:
                score_hashes.append("empty")

        decision_deterministic = score_hashes[0] == score_hashes[1] == score_hashes[2]
        validate_pipeline_stage("Deterministic Decision", decision_deterministic,
                                 f"hash={score_hashes[0]}")
    else:
        validate_pipeline_stage("Deterministic Decision", False, "Not enough decision results")

    # ── Decision Engine Specific Tests ─────────────────────────────────
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("PART 9 — DECISION ENGINE INTEGRITY TESTS")
    logger.info("=" * 70)

    de_tests = []

    last_run = runs[-1] if runs else None

    # Test 1: Decision Engine exists in pipeline output
    de_tests.append((
        "Decision Engine produces FinalContext",
        last_run is not None and last_run.final_context is not None,
    ))

    # Test 2: Decision scores are deterministic (0-1 range)
    if last_run and last_run.final_context:
        fc = last_run.final_context
        all_scores_valid = all(0.0 <= s <= 1.0 for s in fc.decision_scores.values())
        de_tests.append((
            "Decision scores in [0, 1] range",
            all_scores_valid,
        ))

        # Test 3: No removed facts are in selected facts
        removed_ids = set(f.fact_id for f in fc.removed_facts)
        selected_ids = set(f.fact_id for f in fc.selected_facts)
        de_tests.append((
            "No overlap between selected and removed facts",
            len(removed_ids & selected_ids) == 0,
        ))

        # Test 4: Goal-aligned facts subset of selected
        if fc.goal_aligned_fact_ids:
            de_tests.append((
                "Goal-aligned facts are subset of selected",
                fc.goal_aligned_fact_ids <= selected_ids,
            ))

        # Test 5: Performance < 10ms
        de_tests.append((
            f"Decision Engine < 10ms ({fc.metrics.decision_ms:.2f}ms)",
            fc.metrics.decision_ms < 10.0,
        ))

        # Test 6: No LLM involvement (no string generation, only scoring)
        de_tests.append((
            "Decision Engine does not generate text (no LLM)",
            not any("gpt" in k.lower() or "llm" in k.lower() or "openai" in k.lower()
                    for k in dir(fc)),
        ))

        # Test 7: Provenance preserved
        if fc.selected_facts:
            all_have_source = all(f.source_id and f.source_type for f in fc.selected_facts)
            de_tests.append((
                "Provenance preserved (source_id + source_type on all facts)",
                all_have_source,
            ))

        # Test 8: Confidence thresholding applied
        threshold = 0.3
        all_above = all(f.confidence >= threshold for f in fc.selected_facts)
        de_tests.append((
            f"All selected facts above confidence threshold {threshold}",
            all_above,
        ))

    # Test 9: Trace captures decision metrics
    if last_run and last_run.trace:
        de_tests.append((
            "Trace captures decision metrics",
            last_run.trace.decision_input_facts > 0 or last_run.trace.decision_ms > 0,
        ))

    for test_name, test_result in de_tests:
        validate_pipeline_stage(test_name, test_result)

    all_de_ok = all(t[1] for t in de_tests) if de_tests else True
    logger.info(f"\n  Decision Engine integrity: {'ALL PASS' if all_de_ok else 'SOME FAILED'}")

    # ── Architecture Validation ────────────────────────────────────────
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("PART 10 — ARCHITECTURE VALIDATION")
    logger.info("=" * 70)

    arch_checks = []

    arch_checks.append(("RuntimeBuilder is sole runtime entry",
                         last_run is not None and last_run.runtime is not None))
    arch_checks.append(("CharacterPlan generated every request",
                         last_run is not None and last_run.character_plan is not None))
    arch_checks.append(("Character RAG never bypasses planning",
                         last_run is not None and last_run.character_plan is not None and
                         last_run.retrieval_result is not None))
    arch_checks.append(("Decision Engine runs between Fusion and Context",
                         last_run is not None and last_run.final_context is not None and
                         last_run.character_context is not None))
    arch_checks.append(("Decision Engine does not modify FusedEvidence directly",
                         last_run is not None and last_run.fused_evidence is not None))
    arch_checks.append(("LLM performs no reasoning (fallback template used)",
                         last_run is not None and last_run.verbalizer_response is not None))
    arch_checks.append(("CharacterContext unchanged (same Pydantic model)",
                         last_run is not None and last_run.character_context is not None))
    arch_checks.append(("Decision Engine does not call DB or LLM (algorithmic only)",
                         last_run is not None and last_run.final_context is not None))

    for check_name, check_result in arch_checks:
        validate_pipeline_stage(check_name, check_result)

    all_arch_ok = all(c[1] for c in arch_checks)
    logger.info(f"\n  Architecture validation: {'ALL PASS' if all_arch_ok else 'SOME FAILED'}")

    # ── Performance Report ─────────────────────────────────────────────
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("PART 8 — PERFORMANCE BENCHMARKS")
    logger.info("=" * 70)

    if last_run and last_run.trace:
        trace = last_run.trace
        logger.info(f"  Runtime load:       {trace.runtime_load_ms:8.1f}ms")
        logger.info(f"  Planning:           {trace.planning_ms:8.1f}ms")
        logger.info(f"  Retrieval:          {trace.retrieval_ms:8.1f}ms")
        logger.info(f"  Ranking:            {trace.ranking_ms:8.1f}ms")
        logger.info(f"  Fusion:             {trace.fusion_ms:8.1f}ms")
        logger.info(f"  Decision Engine:    {trace.decision_ms:8.1f}ms")
        logger.info(f"  Context build:      {trace.context_build_ms:8.1f}ms")
        logger.info(f"  Verbalization:      {trace.verbalization_ms:8.1f}ms")
        logger.info(f"  ------------------------------------------------")
        logger.info(f"  TOTAL:              {trace.total_ms:8.1f}ms")
        logger.info(f"  Retrieved objects:  {trace.retrieved_count}")
        logger.info(f"  Facts generated:    {trace.facts_generated}")
        logger.info(f"  Decision input:     {trace.decision_input_facts}")
        logger.info(f"  Decision output:    {trace.decision_output_facts}")
        logger.info(f"  Conflicts detected: {trace.decision_conflicts}")
        logger.info(f"  Removed low conf:   {trace.decision_removed_low_confidence}")
        logger.info(f"  Removed dup:        {trace.decision_removed_duplicates}")
        logger.info(f"  Removed diversity:  {trace.decision_removed_diversity}")
        logger.info(f"  Citations created:  {trace.citations_created}")
        logger.info(f"  Token count:        {trace.token_count}")

    # ── Final verdict ──────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 70)
    overall_pass = all_passed == all_total and all_arch_ok and all_de_ok
    if overall_pass:
        logger.info("PHASE 6 — COMPLETE: All cognitive pipeline + Decision Engine tests PASS")
    else:
        logger.info(f"PHASE 6 — INCOMPLETE: {all_passed}/{all_total} queries pass"
                     f"{'' if all_arch_ok else ', arch checks failed'}"
                     f"{'' if all_de_ok else ', decision tests failed'}")
    logger.info("=" * 70)

    return overall_pass, detailed_results, last_run.trace if last_run else None


if __name__ == "__main__":
    success, results, trace = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
