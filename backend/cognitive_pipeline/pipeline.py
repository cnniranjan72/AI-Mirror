"""
Cognitive Pipeline — Integrated Query Execution

Chains RuntimeBuilder → PlannerOrchestrator → Retriever → MemoryRanker → FusionEngine → ContextBuilder → LLMVerbalizer.
One execution path. No bypass. No mock data.
Architecture V3 — FROZEN. No redesign.
"""
import json
import logging
import os
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from backend.character.runtime_builder import RuntimeBuildResult, get_runtime_builder
from backend.cognitive_planning.planner_orchestrator import get_planner_orchestrator
from backend.cognitive_planning.planner_models import CharacterPlan
from backend.rag.retriever import get_retriever, RetrievalResult
from backend.rag.memory_ranker import get_memory_ranker, RankedObject
from backend.rag.fusion import get_fusion_engine, FusedEvidence
from backend.rag.context_builder import get_context_builder, CharacterContext
from backend.verbalizer.verbalizer import get_verbalizer, VerbalizerResponse
from .trace import PipelineTrace
from .decision_engine import get_decision_engine, FinalContext

logger = logging.getLogger(__name__)


@dataclass
class CognitivePipelineResult:
    pipeline_id: str = ""
    user_id: str = ""
    query: str = ""
    success: bool = False
    total_time_ms: float = 0.0
    stages: Dict[str, float] = field(default_factory=dict)

    runtime: Optional[RuntimeBuildResult] = None
    character_plan: Optional[CharacterPlan] = None
    retrieval_result: Optional[RetrievalResult] = None
    ranked_objects: Optional[List[RankedObject]] = None
    fused_evidence: Optional[FusedEvidence] = None
    final_context: Optional["FinalContext"] = None
    character_context: Optional[CharacterContext] = None
    verbalizer_response: Optional[VerbalizerResponse] = None

    errors: List[str] = field(default_factory=list)
    trace: Optional[PipelineTrace] = None

    def summary(self) -> str:
        if not self.success:
            return f"FAIL[{self.user_id}] {self.query[:60]} — {len(self.errors)} errors"
        ctx = self.character_context
        bo = len(ctx.behavior_objects) if ctx else 0
        ev = len(ctx.evidence) if ctx else 0
        inf = len(ctx.inferences) if ctx else 0
        plan = self.character_plan
        intent = plan.intent_plan.intent_type.value if plan else "?"
        resp_len = len(self.verbalizer_response.content) if self.verbalizer_response else 0
        return (
            f"OK[{self.user_id}] intent={intent} "
            f"behaviors={bo} evidence={ev} inferences={inf} "
            f"response={resp_len}ch total={self.total_time_ms:.1f}ms"
        )


class CognitivePipeline:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # Local LLMs (Ollama on CPU) can be slow, especially on the first
        # cold call while the model loads into memory. Keep the timeout
        # generous and env-configurable so verbalization isn't cut off.
        self.pipeline_timeout = self.config.get(
            "pipeline_timeout", float(os.getenv("COGNITIVE_PIPELINE_TIMEOUT", "120"))
        )
        self.runtime_builder = get_runtime_builder()
        self.planner = get_planner_orchestrator()
        self.retriever = get_retriever()
        self.ranker = get_memory_ranker()
        self.fusion = get_fusion_engine()
        self.decision_engine = get_decision_engine()
        self.context_builder = get_context_builder()
        self.verbalizer = get_verbalizer()
        logger.info("CognitivePipeline initialized")

    async def _persist_trace(self, result: CognitivePipelineResult):
        try:
            from app.db.postgres import execute
            tr = result.trace
            if tr is None:
                return
            await execute(
                """
                INSERT INTO pipeline_traces (
                    trace_id, user_id, query,
                    intent_type, intent_confidence, reasoning_mode, plan_confidence,
                    runtime_load_ms, planning_ms, retrieval_ms, ranking_ms,
                    fusion_ms, decision_ms, context_build_ms, verbalization_ms, total_ms,
                    snapshot_id, snapshot_version, self_model_id,
                    inference_count, reflection_count, behavior_object_count, evidence_count,
                    retrieved_count, facts_generated, citations_created, duplicates_removed,
                    aggregate_confidence, decision_input_facts, decision_output_facts,
                    decision_conflicts, token_count, response_length,
                    success, errors, trace_data
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,
                    $17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33,
                    $34,$35::jsonb,$36::jsonb)
                ON CONFLICT (trace_id) DO NOTHING
                """,
                result.pipeline_id,
                result.user_id,
                result.query[:500] if result.query else "",
                tr.intent_type,
                tr.intent_confidence,
                tr.reasoning_mode,
                tr.plan_confidence,
                tr.runtime_load_ms,
                tr.planning_ms,
                tr.retrieval_ms,
                tr.ranking_ms,
                tr.fusion_ms,
                tr.decision_ms,
                tr.context_build_ms,
                tr.verbalization_ms,
                tr.total_ms,
                tr.snapshot_id,
                tr.snapshot_version,
                tr.self_model_id,
                tr.inference_count,
                tr.reflection_count,
                tr.behavior_object_count,
                tr.evidence_count,
                tr.retrieved_count,
                tr.facts_generated,
                tr.citations_created,
                tr.duplicates_removed,
                tr.aggregate_confidence,
                tr.decision_input_facts,
                tr.decision_output_facts,
                tr.decision_conflicts,
                tr.token_count,
                tr.response_length,
                tr.success,
                json.dumps(tr.errors),
                json.dumps(tr.to_dict(), default=str),
            )
        except Exception as e:
            logger.warning(f"Failed to persist trace: {e}")

    async def process_query(
        self,
        user_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> CognitivePipelineResult:
        start = time.perf_counter()
        trace = PipelineTrace(user_id=user_id, query=query)
        result = CognitivePipelineResult(pipeline_id=trace.started_at.strftime("%Y%m%d_%H%M%S_%f"),
                                          user_id=user_id, query=query, trace=trace)
        errors: List[str] = []

        try:
            import asyncio
            result = await asyncio.wait_for(
                self._execute_pipeline(user_id, query, conversation_id, session_id, request_id, result, trace, errors, start, conversation_history),
                timeout=self.pipeline_timeout
            )
            await self._persist_trace(result)
            return result
        except asyncio.TimeoutError:
            total = (time.perf_counter() - start) * 1000
            trace.total_ms = total
            trace.success = False
            err_msg = f"Cognitive pipeline timed out after {self.pipeline_timeout}s"
            logger.error(err_msg)
            errors.append(err_msg)
            result.errors = errors
            result.total_time_ms = total
            await self._persist_trace(result)
            return result
        except Exception as e:
            total = (time.perf_counter() - start) * 1000
            trace.total_ms = total
            trace.success = False
            err_msg = f"Cognitive pipeline failed: {e}"
            logger.error(err_msg, exc_info=True)
            errors.append(err_msg)
            result.errors = errors
            result.total_time_ms = total
            await self._persist_trace(result)
            return result

    async def _execute_pipeline(
        self,
        user_id: str,
        query: str,
        conversation_id: Optional[str],
        session_id: Optional[str],
        request_id: Optional[str],
        result: CognitivePipelineResult,
        trace: PipelineTrace,
        errors: List[str],
        start: float,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> CognitivePipelineResult:
        try:
            # ── Stage 1: Pre-load identity snapshot + inferences from DB ──
            # RuntimeBuilder's snapshot manager only has in-memory cache, and
            # its inference loader calls asyncio.get_running_loop() internally
            # (which raises inside the plain threadpool worker used below, so
            # it always silently returned [] there) — load both from DB first
            # and pass them in to avoid both misses.
            identity_snapshot = await self._load_latest_snapshot_from_db(user_id)
            recent_inferences = await self._load_recent_inferences_from_db(user_id)
            recent_reflections = await self._load_recent_reflections_from_db(user_id)
            identity_source_ids = await self._load_identity_source_ids_from_db(user_id)

            # ── Stage 2: Runtime Builder (offloaded to thread executor) ──
            # build_runtime internally uses asyncio.run_coroutine_threadsafe
            # for DB queries.  Running it in a thread executor avoids the
            # sync-over-async deadlock that would otherwise cause 6 × 5s timeouts.
            t0 = time.perf_counter()
            import asyncio
            loop = asyncio.get_running_loop()
            runtime = await loop.run_in_executor(
                None,
                lambda: self.runtime_builder.build_runtime(
                    user_id=user_id,
                    identity_snapshot=identity_snapshot,
                    current_query=query,
                    conversation_id=conversation_id,
                    session_id=session_id,
                    request_id=request_id,
                    recent_inferences=recent_inferences,
                    recent_reflections=recent_reflections,
                    identity_source_ids=identity_source_ids,
                )
            )
            trace.runtime_load_ms = (time.perf_counter() - t0) * 1000
            logger.info(f"Runtime built: success={runtime.success} in {trace.runtime_load_ms:.1f}ms")

            if not runtime.success:
                errors.extend(runtime.errors)
                return self._finalize(result, errors, start, trace)

            character_core = runtime.character_core
            character_state = runtime.character_state

            if character_core:
                snap = character_core.identity_snapshot
                if snap:
                    trace.snapshot_id = snap.snapshot_id
                    trace.snapshot_version = snap.identity_version
                if character_core.self_model:
                    trace.self_model_id = character_core.self_model.self_model_id
                trace.inference_count = len(character_core.inference_history) if character_core.inference_history else 0
                trace.goal_count = len(character_core.goal_memory_ids) if character_core.goal_memory_ids else 0
                trace.reflection_count = len(character_core.reflection_memory_ids) if character_core.reflection_memory_ids else 0

            # ── Stage 3: Planner ─────────────────────────────────────────
            t0 = time.perf_counter()
            plan = self.planner.build_plan(user_id=user_id, query=query)
            trace.planning_ms = (time.perf_counter() - t0) * 1000
            trace.intent_type = plan.intent_plan.intent_type.value
            trace.intent_confidence = plan.intent_plan.intent_confidence
            trace.reasoning_mode = plan.reasoning_plan.primary_mode.value
            trace.response_structure = plan.response_plan.primary_structure.value
            trace.plan_confidence = plan.overall_confidence
            trace.risk_flags = plan.risk_flags
            trace.retrieval_directives = [d.target.value for d in plan.retrieval_plan.directives]
            logger.info(f"Plan built: {plan.get_summary()} in {trace.planning_ms:.1f}ms")

            # ── Stage 3: Retrieval ────────────────────────────────────────
            # Pre-load context data via async DB queries (avoids deadlock from
            # sync-to-async bridge in registered loaders).
            retrieval_context = await self._load_retrieval_context(user_id)

            # Temporarily clear sync-registered data sources so the retriever
            # falls back to _extract_from_context (which reads our pre-loaded
            # context dict) instead of calling deadlocking sync loaders.
            saved_sources = dict(self.retriever._data_sources)
            self.retriever._data_sources.clear()
            t0 = time.perf_counter()
            retrieval_result = self.retriever.retrieve(plan=plan.retrieval_plan, context=retrieval_context)
            self.retriever._data_sources.update(saved_sources)
            trace.retrieval_ms = (time.perf_counter() - t0) * 1000
            trace.retrieved_count = retrieval_result.total_retrieved
            trace.directives_fulfilled = retrieval_result.directives_fulfilled
            trace.directives_total = retrieval_result.directives_total
            trace.retrieval_errors = retrieval_result.errors
            logger.info(f"Retrieved {retrieval_result.total_retrieved} objects in {trace.retrieval_ms:.1f}ms")

            # ── Stage 4: Memory Ranking ───────────────────────────────────
            identity_topics = None
            goal_ids = None
            if character_core and character_core.identity_snapshot:
                identity_topics = character_core.identity_snapshot.dominant_topics or None
            if character_state:
                goal_ids = [g.goal_id for g in character_state.get_active_goals()]

            t0 = time.perf_counter()
            ranked = self.ranker.rank(
                objects=retrieval_result.objects,
                identity_topics=identity_topics,
                goal_ids=goal_ids,
            )
            trace.ranking_ms = (time.perf_counter() - t0) * 1000
            logger.info(f"Ranked {len(ranked)} objects in {trace.ranking_ms:.1f}ms")

            # ── Stage 5: Evidence Fusion ──────────────────────────────────
            t0 = time.perf_counter()
            fused = self.fusion.fuse(retrieval_result=retrieval_result, ranked_objects=ranked)
            trace.fusion_ms = (time.perf_counter() - t0) * 1000
            trace.facts_generated = fused.facts_generated
            trace.citations_created = fused.citations_created
            trace.duplicates_removed = fused.duplicates_removed
            trace.aggregate_confidence = fused.aggregate_confidence
            logger.info(f"Fused {fused.facts_generated} facts ({fused.citations_created} citations) in {trace.fusion_ms:.1f}ms")

            # ── Stage 6: Decision Engine ──────────────────────────────────
            t0 = time.perf_counter()
            final_ctx = self.decision_engine.decide(
                fused_evidence=fused,
                character_plan=plan,
                retrieval_result=retrieval_result,
                ranked_objects=ranked,
                retrieval_context=retrieval_context,
            )
            trace.decision_ms = (time.perf_counter() - t0) * 1000
            trace.decision_input_facts = final_ctx.metrics.input_facts
            trace.decision_output_facts = final_ctx.metrics.final_facts
            trace.decision_conflicts = final_ctx.metrics.conflicts_detected
            trace.decision_removed_low_confidence = final_ctx.metrics.removed_low_confidence
            trace.decision_removed_duplicates = final_ctx.metrics.removed_duplicates
            trace.decision_removed_diversity = final_ctx.metrics.removed_diversity
            logger.info(
                f"Decision Engine: {final_ctx.metrics.input_facts} → {final_ctx.metrics.final_facts} facts "
                f"({final_ctx.metrics.removed_low_confidence} low_conf, "
                f"{final_ctx.metrics.removed_duplicates} dup, "
                f"{final_ctx.metrics.removed_diversity} diversity, "
                f"{final_ctx.metrics.conflicts_detected} conflicts) "
                f"in {trace.decision_ms:.1f}ms"
            )

            # ── Stage 7: Context Construction ─────────────────────────────
            # Uses Decision Engine's filtered data for a more relevant context.
            t0 = time.perf_counter()
            filtered_fused = FusedEvidence(
                facts=final_ctx.selected_facts,
                fusion_time_ms=fused.fusion_time_ms,
                total_sources_merged=fused.total_sources_merged,
                facts_generated=len(final_ctx.selected_facts),
                duplicates_removed=fused.duplicates_removed + len(final_ctx.removed_facts),
                citations_created=len([f for f in final_ctx.selected_facts if f.citation_id]),
                aggregate_confidence=(
                    sum(f.confidence for f in final_ctx.selected_facts) / len(final_ctx.selected_facts)
                    if final_ctx.selected_facts else fused.aggregate_confidence
                ),
            )
            # Categorize the character's grounding data (behavior objects,
            # evidence, inferences) from the FULL retrieval so the context is
            # not starved by the decision engine's fact-level filtering. The
            # decision-selected facts still drive the response claims via
            # filtered_fused below.
            # The two audits, computed by their own deterministic scorers so the
            # twin can discuss its own findings. Failures are swallowed: chat
            # answering without the audit is a lesser harm than chat not
            # answering at all, and both scorers already degrade internally.
            platform_audit, interest_provenance = await self._load_audit_findings(user_id)

            ctx = self.context_builder.build(
                user_id=user_id,
                retrieval_result=retrieval_result,
                character_plan=plan,
                fused_evidence=filtered_fused,
                identity_snapshot=final_ctx.identity_snapshot or None,
                self_model=final_ctx.self_model or None,
                platform_audit=platform_audit,
                interest_provenance=interest_provenance,
            )
            trace.context_build_ms = (time.perf_counter() - t0) * 1000
            trace.context_id = ctx.context_id
            trace.behavior_object_count = len(ctx.behavior_objects)
            trace.evidence_count = len(ctx.evidence)
            logger.info(f"Context built: {ctx.get_summary()} in {trace.context_build_ms:.1f}ms")

            # ── Stage 7: Verbalization ────────────────────────────────────
            t0 = time.perf_counter()
            from app.services.user_llm_config import get_resolved_llm_config
            llm_override = await get_resolved_llm_config(user_id)
            vresponse = await self.verbalizer.verbalize(
                context=ctx, plan=plan, conversation_history=conversation_history, override=llm_override,
            )

            trace.verbalization_ms = (time.perf_counter() - t0) * 1000
            trace.token_count = vresponse.token_count
            trace.response_length = len(vresponse.content)
            trace.provider = vresponse.provider
            trace.model = vresponse.model
            trace.response = vresponse.content
            logger.info(f"Verbalized {vresponse.token_count} tokens in {trace.verbalization_ms:.1f}ms")

            # ── Assemble result ───────────────────────────────────────────
            total = (time.perf_counter() - start) * 1000
            trace.total_ms = total
            trace.success = True
            result.success = True
            result.total_time_ms = total
            result.stages = {
                "runtime_load_ms": trace.runtime_load_ms,
                "planning_ms": trace.planning_ms,
                "retrieval_ms": trace.retrieval_ms,
                "ranking_ms": trace.ranking_ms,
                "fusion_ms": trace.fusion_ms,
                "decision_ms": trace.decision_ms,
                "context_build_ms": trace.context_build_ms,
                "verbalization_ms": trace.verbalization_ms,
            }
            result.runtime = runtime
            result.character_plan = plan
            result.retrieval_result = retrieval_result
            result.ranked_objects = ranked
            result.fused_evidence = fused
            result.final_context = final_ctx
            result.character_context = ctx
            result.verbalizer_response = vresponse

            logger.info(f"Cognitive pipeline completed: {result.summary()}")
            return result

        except Exception as e:
            total = (time.perf_counter() - start) * 1000
            trace.total_ms = total
            trace.success = False
            err_msg = f"Cognitive pipeline failed: {e}"
            logger.error(err_msg, exc_info=True)
            errors.append(err_msg)
            result.errors = errors
            result.total_time_ms = total
            return result

    def _finalize(
        self,
        result: CognitivePipelineResult,
        errors: List[str],
        start: float,
        trace: PipelineTrace,
    ) -> CognitivePipelineResult:
        result.errors = errors
        result.total_time_ms = (time.perf_counter() - start) * 1000
        trace.total_ms = result.total_time_ms
        trace.success = False
        return result

    async def _load_latest_snapshot_from_db(self, user_id: str):
        """Load latest IdentitySnapshot from DB as a raw dict."""
        try:
            from app.db.postgres import fetchrow
            import json
            row = await fetchrow(
                "SELECT * FROM identity_snapshots WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
                user_id
            )
            if not row:
                logger.warning(f"No identity snapshot found in DB for user {user_id}")
                return None
            from backend.identity.identity_snapshot import IdentitySnapshot
            from backend.identity.identity_engine import (
                BehaviorProfile, InterestGraph, CreatorGraph, LearningStyle,
                AttentionProfile, ExplorationProfile, ConsistencyProfile,
                HabitProfile, MotivationSignals,
            )

            d = dict(row)
            for key in ("dominant_topics", "emerging_topics", "personality_traits", "interest_graph", "metadata"):
                if isinstance(d.get(key), str):
                    try: d[key] = json.loads(d[key])
                    except Exception: pass
                elif d.get(key) is None:
                    d[key] = {} if key in ("personality_traits", "interest_graph", "metadata") else []

            snap = IdentitySnapshot.model_construct(
                snapshot_id=d["snapshot_id"],
                identity_id=d["identity_id"],
                user_id=d["user_id"],
                identity_version=d["identity_version"],
                snapshot_timestamp=d.get("snapshot_timestamp") or d.get("created_at"),
                dominant_topics=d.get("dominant_topics", []),
                emerging_topics=d.get("emerging_topics", []),
                overall_confidence=float(d.get("overall_confidence", 0.0) or 0.0),
                identity_completeness=float(d.get("identity_completeness", 0.0) or 0.0),
                personality_traits=d.get("personality_traits", {}),
                behavior_profile=BehaviorProfile(avg_engagement_rate=0.0, avg_watch_time=0.0, behavior_diversity=0.0, behavior_stability=0.0),
                interest_graph=InterestGraph(diversity_score=0.0),
                creator_graph=CreatorGraph(creator_diversity_score=0.0, dependence_score=0.0),
                learning_style=LearningStyle(style_type="unknown", confidence=0.0, completion_rate=0.0, depth_preference="unknown", pace_preference="unknown"),
                attention_profile=AttentionProfile(avg_attention_span=0.0, attention_consistency=0.0, attention_trend="unknown", distraction_resistance=0.0, focus_quality=0.0),
                exploration_profile=ExplorationProfile(novelty_seeking_score=0.0, exploration_rate=0.0, exploitation_rate=0.0, topic_switching_frequency=0.0, comfort_zone_ratio=0.0),
                consistency_profile=ConsistencyProfile(overall_consistency=0.0, topic_consistency=0.0, temporal_consistency=0.0, engagement_consistency=0.0, volatility_score=0.0),
                habit_profile=HabitProfile(has_daily_routine=False, routine_strength=0.0, session_regularity=0.0, habit_stability=0.0),
                motivation_signals=MotivationSignals(learning_motivation=0.0, entertainment_seeking=0.0, skill_building_intent=0.0, curiosity_score=0.0, goal_orientation=0.0, intrinsic_motivation=0.0, confidence=0.0),
                metadata=d.get("metadata", {}),
            )
            logger.info(f"Loaded identity snapshot {snap.snapshot_id} v{snap.identity_version} from DB")
            return snap
        except Exception as e:
            logger.warning(f"Error loading identity snapshot from DB: {e}")
            return None

    async def _load_recent_inferences_from_db(self, user_id: str, limit: int = 20):
        """Load the user's recent Inference rows for CharacterCore.inference_history.
        See RuntimeBuilder._load_recent_inferences docstring for why this must be
        pre-loaded here rather than left to that method's internal (broken inside
        a threadpool worker) DB bridge."""
        try:
            from app.db.postgres import fetch
            import json
            from backend.reasoning.inference_engine import Inference

            rows = await fetch(
                "SELECT * FROM inferences WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
                user_id, limit,
            )

            def _j(v, default):
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        return default
                return v if v is not None else default

            inferences = []
            for row in rows:
                d = dict(row)
                inferences.append(Inference(
                    inference_id=d["inference_id"],
                    inference_type=d["inference_type"],
                    label=d["label"],
                    description=d["description"],
                    confidence=float(d["confidence"] or 0.0),
                    importance=float(d["importance"] or 0.0),
                    strength=float(d["strength"] or 0.0),
                    supporting_evidence=_j(d.get("supporting_evidence"), []),
                    evidence_summary=d.get("evidence_summary") or "",
                    affected_topics=_j(d.get("affected_topics"), []),
                    affected_creators=_j(d.get("affected_creators"), []),
                    affected_behaviors=_j(d.get("affected_behaviors"), []),
                    recommendation_seed=d.get("recommendation_seed"),
                    suggested_actions=_j(d.get("suggested_actions"), []),
                    inferred_at=d.get("inferred_at") or d["created_at"],
                    valid_from=d.get("valid_from") or d["created_at"],
                    valid_until=d.get("valid_until"),
                    rule_name=d.get("rule_name"),
                    context_id=d.get("context_id"),
                    metadata=_j(d.get("metadata"), {}),
                ))
            return inferences
        except Exception as e:
            logger.warning(f"Error loading recent inferences from DB: {e}")
            return []

    async def _load_recent_reflections_from_db(self, user_id: str, limit: int = 5):
        """Load the user's recent Reflection rows for CharacterCore.reflection_memory_ids.
        Same pre-load reasoning as _load_recent_inferences_from_db above — RuntimeBuilder's
        internal loader can't reach a running event loop from inside a threadpool worker."""
        try:
            from app.db.postgres import fetch
            import json
            from backend.reasoning.reasoning_context import ReflectionReference

            rows = await fetch(
                "SELECT reflection_id, reflection_type, key_insights, confidence, created_at "
                "FROM reflections WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
                user_id, limit,
            )

            reflections = []
            for row in rows:
                key_insights = row["key_insights"]
                if isinstance(key_insights, str):
                    try:
                        key_insights = json.loads(key_insights)
                    except Exception:
                        key_insights = []
                reflections.append(ReflectionReference(
                    reflection_id=row["reflection_id"],
                    reflection_type=row["reflection_type"],
                    reflection_date=row["created_at"],
                    key_insights=key_insights or [],
                    relevance_score=float(row["confidence"] or 0.0),
                ))
            return reflections
        except Exception as e:
            logger.warning(f"Error loading recent reflections from DB: {e}")
            return []

    async def _load_identity_source_ids_from_db(self, user_id: str) -> Dict[str, list]:
        """Load the live identity's source behavior-object/evidence IDs, used to
        populate the character's memory reference IDs (there is no separate
        'memories' table with a writer anywhere in the system)."""
        try:
            from app.db.postgres import fetchrow
            import json

            row = await fetchrow(
                "SELECT source_behavior_objects, source_evidence FROM identities WHERE user_id = $1",
                user_id,
            )
            if not row:
                return {"behavior_objects": [], "evidence": []}

            def _j(v):
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        return []
                return v or []

            return {
                "behavior_objects": _j(row["source_behavior_objects"]),
                "evidence": _j(row["source_evidence"]),
            }
        except Exception as e:
            logger.warning(f"Error loading identity source IDs from DB: {e}")
            return {"behavior_objects": [], "evidence": []}

    def _ensure_str_ids(self, row_dict: dict) -> dict:
        for col in ("id",):
            v = row_dict.get(col)
            if v is not None and not isinstance(v, str):
                row_dict[col] = str(v)
        return row_dict

    async def _load_audit_findings(self, user_id: str):
        """Platform-profile audit and interest provenance, for chat context.

        Both are skipped silently when they have nothing to say (no imported
        claims, no deliberate signal), so an account that has never imported an
        export pays nothing for this. Their own reliability flags travel with
        them; the verbalizer refuses to state a verdict the scorer withheld.
        """
        platform_audit: Dict[str, Any] = {}
        provenance: Dict[str, Any] = {}

        try:
            from app.db.postgres import fetchrow
            from app.services import algorithmic_mirror, interest_provenance as prov

            # Cheap existence check first: computing an audit for a user with no
            # imported claims would embed topics and hit the network for nothing
            # on every single chat message.
            claim_row = await fetchrow(
                "SELECT COUNT(*) AS c FROM platform_profile_claims WHERE user_id = $1",
                user_id,
            )
            if claim_row and claim_row["c"]:
                platform_audit = await algorithmic_mirror.build_mirror_report(user_id)

            signal_row = await fetchrow(
                "SELECT COUNT(*) AS c FROM search_signals WHERE user_id = $1",
                user_id,
            )
            if signal_row and signal_row["c"]:
                provenance = await prov.build_provenance_report(user_id)
        except Exception as e:
            logger.warning("Audit findings unavailable for chat context: %s", e)

        return platform_audit, provenance

    async def _load_retrieval_context(self, user_id: str) -> Dict[str, Any]:
        """Load retrieval context data via async DB queries."""
        import json
        ctx: Dict[str, Any] = {}
        try:
            from app.db.postgres import fetch, fetchrow

            # Behavior objects
            bo_rows = await fetch(
                "SELECT * FROM behavior_objects WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 50",
                user_id
            )
            ctx["behavior_objects"] = []
            for row in bo_rows:
                d = self._ensure_str_ids(dict(row))
                for key in ("evidence_references", "hashtags", "related_topics", "engagement_statistics", "watch_statistics", "temporal_statistics", "trend_information", "subtopics", "keywords", "creators", "tags", "metadata"):
                    if isinstance(d.get(key), str):
                        try: d[key] = json.loads(d[key])
                        except Exception: pass
                    elif d.get(key) is None: d[key] = [] if key not in ("engagement_statistics", "watch_statistics", "temporal_statistics", "trend_information", "metadata") else {}
                ctx["behavior_objects"].append(d)

            # Evidence
            ev_rows = await fetch(
                "SELECT * FROM evidence WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50",
                user_id
            )
            ctx["evidence"] = []
            for row in ev_rows:
                d = self._ensure_str_ids(dict(row))
                for key in ("supporting_behavior_objects", "supporting_evidence_ids", "metadata"):
                    if isinstance(d.get(key), str):
                        try: d[key] = json.loads(d[key])
                        except Exception: pass
                    elif d.get(key) is None: d[key] = [] if key != "metadata" else {}
                ctx["evidence"].append(d)

            # Identity snapshot
            snap_row = await fetchrow(
                "SELECT * FROM identity_snapshots WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
                user_id
            )
            if snap_row:
                d = self._ensure_str_ids(dict(snap_row))
                for key in ("dominant_topics", "emerging_topics", "interest_graph", "personality_traits"):
                    if isinstance(d.get(key), str):
                        try: d[key] = json.loads(d[key])
                        except Exception: pass
                    elif d.get(key) is None: d[key] = [] if key not in ("interest_graph", "personality_traits") else {}
                ctx["identity_snapshot"] = d

            # Self model
            sm_row = await fetchrow(
                "SELECT * FROM self_models WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 1",
                user_id
            )
            if sm_row:
                d = self._ensure_str_ids(dict(sm_row))
                for key in ("beliefs", "strong_beliefs", "uncertain_beliefs", "metadata"):
                    if isinstance(d.get(key), str):
                        try: d[key] = json.loads(d[key])
                        except Exception: pass
                    elif d.get(key) is None: d[key] = [] if key != "uncertainty_map" else {}
                ctx["self_model"] = d

            # Inferences
            inf_rows = await fetch(
                "SELECT * FROM inferences WHERE user_id = $1 ORDER BY created_at DESC LIMIT 30",
                user_id
            )
            ctx["inferences"] = []
            for row in inf_rows:
                d = self._ensure_str_ids(dict(row))
                for key in ("supporting_evidence", "affected_topics", "affected_creators", "affected_behaviors", "suggested_actions", "metadata"):
                    if isinstance(d.get(key), str):
                        try: d[key] = json.loads(d[key])
                        except Exception: pass
                    elif d.get(key) is None: d[key] = [] if key != "metadata" else {}
                ctx["inferences"].append(d)

            # Goals
            goal_rows = await fetch(
                "SELECT * FROM goals WHERE user_id = $1 AND status = 'active' ORDER BY alignment_score ASC, created_at DESC LIMIT 10",
                user_id
            )
            ctx["goals"] = []
            for row in goal_rows:
                d = self._ensure_str_ids(dict(row))
                for key in ("milestones", "metadata"):
                    if isinstance(d.get(key), str):
                        try: d[key] = json.loads(d[key])
                        except Exception: pass
                    elif d.get(key) is None: d[key] = [] if key != "metadata" else {}
                ctx["goals"].append(d)

            # Reflections
            ref_rows = await fetch(
                "SELECT * FROM reflections WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20",
                user_id
            )
            ctx["reflections"] = []
            for row in ref_rows:
                d = self._ensure_str_ids(dict(row))
                for key in ("key_insights", "metrics", "patterns_identified", "changes_detected", "recommendations", "memory_refs", "metadata"):
                    if isinstance(d.get(key), str):
                        try: d[key] = json.loads(d[key])
                        except Exception: pass
                    elif d.get(key) is None: d[key] = [] if key not in ("metrics", "metadata") else {}
                ctx["reflections"].append(d)

            logger.debug(f"Loaded retrieval context: {len(ctx.get('behavior_objects', []))} bos, "
                         f"{len(ctx.get('evidence', []))} ev, {len(ctx.get('inferences', []))} inf, "
                         f"{'snap' if 'identity_snapshot' in ctx else 'no snap'}, "
                         f"{'sm' if 'self_model' in ctx else 'no sm'}")
        except Exception as e:
            logger.warning(f"Error loading retrieval context: {e}")
        return ctx


_pipeline_instance: Optional[CognitivePipeline] = None


def get_cognitive_pipeline() -> CognitivePipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = CognitivePipeline()
    return _pipeline_instance
