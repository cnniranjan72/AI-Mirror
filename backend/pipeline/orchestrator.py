"""
V3 Pipeline Orchestrator
Coordinates the complete V3 execution flow:
Events → Normalize → Consolidate → BehaviorObjects → Evidence → Inference → Identity → Snapshot → SelfModel

Architecture V3 — FROZEN
No redesign. No new abstractions. Integration only.
"""
import json

import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from backend.shared.contracts import BehaviorEvent
from backend.reasoning.behavior_object import BehaviorObject
from backend.reasoning.evidence_engine import EvidenceEngine, Evidence
from backend.reasoning.inference_engine import InferenceEngine, Inference
from backend.reasoning.reflection_engine import ReflectionEngine, Reflection
from backend.reasoning.reasoning_context import ReasoningContext, TemporalContext
from backend.reasoning.rules import RuleEngine
from backend.engines.knowledge_consolidation import KnowledgeConsolidationEngine, CONFIDENCE_SATURATION_COUNT
from backend.identity.identity_engine import IdentityEngine, Identity
from backend.identity.identity_evolution import IdentityEvolutionEngine, IdentityEvolution
from backend.identity.identity_snapshot import IdentitySnapshot, SnapshotManager
from backend.identity.self_model import SelfModelEngine, SelfModel

from app.db.postgres import fetch, fetchrow, execute
from pipeline import stored_events

logger = logging.getLogger(__name__)

# Occurrence counts at which these scores saturate to 1.0. Previously 100/50,
# calibrated for power-user volumes — realistic per-topic occurrence is single
# digits to low tens, so these never rose above ~0.05-0.20. See
# knowledge_consolidation.CONFIDENCE_SATURATION_COUNT for the matching rationale.
IMPORTANCE_SATURATION_COUNT = 20.0
STABILITY_SATURATION_COUNT = 10.0


def _trend_direction_for(cluster) -> str:
    """The deprecated trend field, kept consistent with the real lifecycle.

    Only recency is available at this point - the trajectory needs event
    timestamps, which the lifecycle sweep supplies later - so this reports
    "stable" rather than guessing a direction it cannot see.
    """
    from backend.reasoning.lifecycle import evaluate_lifecycle

    state, _ = evaluate_lifecycle(
        {"last_seen": cluster.last_seen, "first_seen": cluster.first_seen,
         "occurrence_count": cluster.occurrence_count,
         "daily_frequency": cluster.growth_rate},
        {},
    )
    # TrendDirection has no "archived"; that distinction lives in
    # lifecycle_state, which is the field to read.
    return "dormant" if state == "archived" else state


class V3PipelineResult:
    """Result of running the complete V3 pipeline"""
    def __init__(self):
        self.behavior_objects: List[BehaviorObject] = []
        self.evidence: List[Evidence] = []
        self.inferences: List[Inference] = []
        self.reflection: Optional[Reflection] = None
        self.identity: Optional[Identity] = None
        self.snapshot: Optional[IdentitySnapshot] = None
        self.self_model: Optional[SelfModel] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []


class V3Pipeline:
    """
    V3 Pipeline Orchestrator
    
    Single pipeline that every event traverses:
    Events → Behavior Gateway → Consolidation → BehaviorObjects
    → Evidence → Inference → Identity → Snapshot → SelfModel
    
    This is the ONLY execution path for new events.
    """
    
    def __init__(self):
        self.evidence_engine = EvidenceEngine()
        self.reflection_engine = ReflectionEngine()
        self.inference_engine = InferenceEngine()
        self.rule_engine = RuleEngine()
        self.knowledge_engine = KnowledgeConsolidationEngine()
        self.identity_engine = IdentityEngine()
        self.evolution_engine = IdentityEvolutionEngine()
        self.snapshot_manager = SnapshotManager()
        self.self_model_engine = SelfModelEngine()
        
        logger.info("V3Pipeline initialized")
    
    async def run(
        self,
        user_id: str,
        events: List[BehaviorEvent],
        existing_identity: Optional[Identity] = None,
        existing_evolution: Optional[IdentityEvolution] = None
    ) -> V3PipelineResult:
        """
        Run the complete V3 pipeline for a batch of events.
        
        Args:
            user_id: User identifier
            events: Normalized BehaviorEvents
            existing_identity: Optional existing identity to evolve
            existing_evolution: Optional evolution record
            
        Returns:
            V3PipelineResult with all pipeline outputs
        """
        result = V3PipelineResult()
        
        try:
            logger.info(f"Running V3 pipeline for user {user_id} with {len(events)} events")
            
            # Step 1: Knowledge Consolidation (events → clusters → behavior objects)
            step1_result = await self._consolidate_events(user_id, events)
            result.behavior_objects = step1_result
            
            # Step 2: Evidence Collection (behavior objects → evidence)
            step2_result = self._collect_evidence(user_id, events, result.behavior_objects)
            result.evidence = step2_result
            
            # Step 3: Inference (evidence → inferences)
            step3_result = self._generate_inferences(
                user_id, result.behavior_objects, result.evidence
            )
            result.inferences = step3_result
            
            # Step 4: Reflection (behavior objects + evidence + inferences → reflection)
            step4_reflection = self._generate_reflection(
                user_id, result.behavior_objects, result.evidence, result.inferences
            )
            result.reflection = step4_reflection

            # Step 5: Identity Construction/Update (inferences + evidence → identity)
            # Identity confidence must reflect ALL evidence ever collected for this
            # user, not just this batch's few items — otherwise it's dominated by
            # whatever small slice of evidence happened to be generated in the
            # latest ingest. Load the full accumulated set (mirrors how behavior
            # objects are already loaded in full in _consolidate_events).
            all_evidence_for_identity = await self._load_all_evidence(user_id, exclude_ids={e.evidence_id for e in result.evidence})
            all_evidence_for_identity += result.evidence

            step5_result = await self._construct_identity(
                user_id, result.behavior_objects, result.inferences,
                all_evidence_for_identity, existing_identity, existing_evolution
            )
            result.identity = step5_result["identity"]
            result.snapshot = step5_result["snapshot"]
            result.self_model = step5_result["self_model"]
            if not existing_identity and step5_result.get("evolution"):
                existing_evolution = step5_result["evolution"]
            
            # Persist everything
            await self._persist_all(user_id, result)

            # Every behaviour this user has, not only the ones in this
            # batch. A topic they have abandoned never appears in a batch
            # again, so without this sweep the only path that could mark
            # it dormant is unreachable for exactly the behaviours that
            # need it.
            await self._refresh_lifecycles(user_id)

            # The recall index. The memories table has existed since the
            # original schema with five indexes on it and never had a writer;
            # timeline.py has been querying it on every request and receiving
            # nothing, and memory_question plans it as a required source.
            try:
                from backend.app.services.memory_store import write_from_pipeline
                await write_from_pipeline(
                    user_id,
                    behavior_objects=result.behavior_objects,
                    inferences=result.inferences,
                    reflection=result.reflection,
                )
            except Exception as e:
                logger.error("Recall index write failed for %s: %s", user_id, e)
            
            logger.info(f"V3 pipeline complete: {len(result.behavior_objects)} behaviors, "
                       f"{len(result.evidence)} evidence, {len(result.inferences)} inferences, "
                       f"identity={'created' if result.identity else 'updated'}")
            
            return result
            
        except Exception as e:
            logger.error(f"V3 pipeline failed: {str(e)}", exc_info=True)
            result.errors.append(str(e))
            return result
    
    async def _consolidate_events(
        self,
        user_id: str,
        events: List[BehaviorEvent]
    ) -> List[BehaviorObject]:
        """Step 1: Consolidate events into behavior objects"""
        try:
            # Load existing behavior objects from database
            existing_behavior_ids = await self._load_behavior_object_ids(user_id)
            existing_behavior_objects = await self._load_behavior_objects(user_id)

            # Consolidate over a window of the account's recent events, not
            # only the ones in this request. A cluster needs three events
            # sharing a topic or creator; applied per request, that meant a
            # creator whose videos were spread across the extension's
            # ten-event batches never reached three in any one of them and
            # never became anything. Measured against the same events
            # consolidated together, batches of ten lose 19-50% of an
            # account's topics, nearly all of them creators.
            #
            # The window is read back from storage rather than kept in memory
            # because the process that saw the earlier batches is long gone.
            stored = await stored_events.load_recent(user_id)
            to_consolidate = stored_events.merge(stored, events)
            if len(to_consolidate) > len(events):
                logger.info(
                    "Consolidating %d events (%d from this batch, %d from history)",
                    len(to_consolidate), len(events), len(to_consolidate) - len(events),
                )

            clusters, unclustered = self.knowledge_engine.consolidate_events(
                events=to_consolidate,
                existing_clusters=[],
            )
            
            # Convert clusters to behavior objects
            behavior_objects = list(existing_behavior_objects)
            
            skipped: List[str] = []
            for cluster in clusters:
                try:
                    existing = None
                    for bo in behavior_objects:
                        if bo.topic == cluster.primary_topic:
                            existing = bo
                            break
                
                    if existing:
                        existing.update_version()
                        existing.supporting_event_ids = list(set(
                            existing.supporting_event_ids + cluster.event_ids
                        ))
                        # occurrence_count must reflect ALL events ever consolidated into
                        # this topic, not just the latest batch — supporting_event_ids is
                        # the accumulated (deduped) set, so its length is the true count.
                        # Previously this was overwritten with cluster.occurrence_count
                        # (the new batch's size alone), so a topic revisited many times
                        # over many ingests never accumulated past a handful.
                        true_occurrence_count = len(existing.supporting_event_ids)
                        existing.temporal_statistics.occurrence_count = true_occurrence_count
                        existing.temporal_statistics.last_seen = cluster.last_seen
                        # confidence/importance/stability were also frozen at whatever the
                        # topic's FIRST tiny batch produced — recompute from the true
                        # accumulated count so an established, recurring pattern actually
                        # reads as confident.
                        existing.confidence_score = min(1.0, true_occurrence_count / CONFIDENCE_SATURATION_COUNT)
                        existing.importance_score = min(1.0, true_occurrence_count / IMPORTANCE_SATURATION_COUNT)
                        existing.stability_score = min(1.0, true_occurrence_count / STABILITY_SATURATION_COUNT)
                        if cluster.creators:
                            existing.creators = list(set(existing.creators + cluster.creators))
                    else:
                        from datetime import timedelta
                        stats = self._cluster_to_engagement(cluster)
                        bo = BehaviorObject(
                            unique_id=f"bo_{cluster.cluster_id}",
                            topic=cluster.primary_topic,
                            subtopics=cluster.related_topics,
                            representative_embedding=cluster.metadata.get(
                                "representative_embedding", [0.0] * 384
                            ) if isinstance(cluster.metadata, dict) else [0.0] * 384,
                            keywords=cluster.keywords,
                            creators=cluster.creators or [],
                            creator_diversity_score=min(1.0, len(cluster.creators or []) / 10.0),
                            engagement_statistics=stats["engagement"],
                            watch_statistics=stats["watch"],
                            temporal_statistics=stats["temporal"],
                            trend_information=stats["trend"],
                            lifecycle_state=self._lifecycle_for(stats),
                            importance_score=min(1.0, cluster.occurrence_count / IMPORTANCE_SATURATION_COUNT),
                            confidence_score=cluster.confidence,
                            stability_score=min(1.0, cluster.occurrence_count / STABILITY_SATURATION_COUNT),
                            evidence_references=[],
                            supporting_event_ids=cluster.event_ids,
                            supporting_cluster_ids=[cluster.cluster_id],
                            evolution_history=[],
                            version=1,
                            created_at=cluster.created_at,
                            updated_at=cluster.updated_at,
                            metadata={
                                "cluster_type": cluster.cluster_type,
                                "source": "knowledge_consolidation"
                            },
                            tags=[]
                        )
                        behavior_objects.append(bo)
                except Exception as e:
                    # One malformed cluster must cost that topic, not the twin.
                    # This construction sat under a single try/except that
                    # returned [] for the whole step, so one out-of-range value
                    # produced a user with no behaviour objects, therefore no
                    # inferences, no identity worth the name and an empty
                    # Report — logged, but indistinguishable from "no data yet".
                    skipped.append(cluster.primary_topic)
                    logger.warning(
                        "Skipped cluster %s (%s): %s",
                        cluster.cluster_id, cluster.primary_topic, e,
                    )

            if skipped:
                logger.warning(
                    "Consolidation skipped %d of %d clusters: %s",
                    len(skipped), len(clusters), skipped[:10],
                )
            logger.info(f"Consolidation: {len(behavior_objects)} behavior objects from {len(events)} events")
            return behavior_objects
            
        except Exception as e:
            logger.error(f"Consolidation failed: {str(e)}", exc_info=True)
            return []
    
    def _collect_evidence(
        self,
        user_id: str,
        events: List[BehaviorEvent],
        behavior_objects: List[BehaviorObject]
    ) -> List[Evidence]:
        """Step 2: Collect evidence across all 5 dimensions"""
        try:
            evidence_list = []

            for bo in behavior_objects:
                tev = self.evidence_engine.collect_topical_evidence(
                    events=events, topic=bo.topic
                )
                if tev:
                    tev.supporting_behavior_objects = [bo.unique_id]
                    evidence_list.append(tev)

                for creator in bo.creators:
                    ce = self.evidence_engine.collect_creator_evidence(
                        events=events, creator=creator
                    )
                    if ce:
                        ce.supporting_behavior_objects = [bo.unique_id]
                        evidence_list.append(ce)

            tev = self.evidence_engine.collect_temporal_evidence(
                events=events,
                pattern_description="Temporal usage patterns from this batch"
            )
            if tev:
                evidence_list.append(tev)

            iev = self.evidence_engine.collect_interaction_evidence(
                events=events
            )
            if iev:
                evidence_list.append(iev)

            evidence_list = self.evidence_engine.merge_similar_evidence(evidence_list)
            evidence_list = self.evidence_engine.rank_evidence(evidence_list)

            logger.info(f"Evidence collected: {len(evidence_list)} items across 5 dimensions")
            return evidence_list

        except Exception as e:
            logger.error(f"Evidence collection failed: {str(e)}", exc_info=True)
            return []
    
    def _generate_inferences(
        self,
        user_id: str,
        behavior_objects: List[BehaviorObject],
        evidence: List[Evidence]
    ) -> List[Inference]:
        """Step 3: Generate inferences from evidence and behavior objects"""
        try:
            if not behavior_objects:
                return []
            
            now = datetime.utcnow()
            temporal_context = TemporalContext(
                current_time=now,
                time_window_start=now - timedelta(days=30),
                time_window_end=now,
                time_of_day="morning",
                day_of_week=now.strftime("%A"),
                is_weekend=now.weekday() >= 5
            )
            
            context = ReasoningContext(
                context_id=f"ctx_{now.timestamp()}",
                created_at=now,
                behavior_objects=behavior_objects,
                evidence=evidence,
                overall_confidence=(
                    sum(e.confidence for e in evidence) / len(evidence)
                    if evidence else 0.5
                ),
                temporal_context=temporal_context,
                user_id=user_id
            )
            
            inferences = self.inference_engine.infer_from_context(context)
            inferences = self.inference_engine.rank_inferences(inferences)
            
            logger.info(f"Inferences generated: {len(inferences)} from {len(evidence)} evidence items")
            return inferences
            
        except Exception as e:
            logger.error(f"Inference generation failed: {str(e)}", exc_info=True)
            return []

    def _generate_reflection(
        self,
        user_id: str,
        behavior_objects: List[BehaviorObject],
        evidence_list: List[Evidence],
        inferences: List[Inference],
    ) -> Optional[Reflection]:
        try:
            ref = self.reflection_engine.generate_reflection(
                user_id=user_id,
                behavior_objects=behavior_objects,
                evidence_list=evidence_list,
                inferences=inferences,
            )
            if ref:
                logger.info(f"Reflection generated: {ref.reflection_id}")
            return ref
        except Exception as e:
            logger.error(f"Reflection generation failed: {str(e)}", exc_info=True)
            return None
    
    async def _construct_identity(
        self,
        user_id: str,
        behavior_objects: List[BehaviorObject],
        inferences: List[Inference],
        evidence: List[Evidence],
        existing_identity: Optional[Identity] = None,
        existing_evolution: Optional[IdentityEvolution] = None
    ) -> Dict[str, Any]:
        """Step 4: Construct or evolve identity"""
        try:
            if existing_identity:
                # Drift is measured against the last snapshot that actually
                # made it to storage, and a snapshot is forced when the newest
                # one is older than the max age — so the history gets periodic
                # anchors even for an identity that never moves much.
                baseline_snapshot, snapshot_age_hours = await self._load_baseline_snapshot(
                    existing_identity.identity_id
                )
                max_age = float(os.getenv("SNAPSHOT_MAX_AGE_HOURS", "24"))
                force_snapshot = (
                    baseline_snapshot is None
                    or (snapshot_age_hours is not None and snapshot_age_hours >= max_age)
                )

                identity, snapshot, evolution = self.evolution_engine.evolve_identity(
                    identity=existing_identity,
                    new_behaviors=behavior_objects,
                    new_inferences=inferences,
                    new_evidence=evidence,
                    evolution=existing_evolution,
                    baseline_snapshot=baseline_snapshot,
                    force_snapshot=force_snapshot,
                )
            else:
                identity = self.identity_engine.construct_identity(
                    user_id=user_id,
                    behavior_objects=behavior_objects,
                    inferences=inferences,
                    evidence=evidence
                )
                snapshot = self.snapshot_manager.create_snapshot(identity)
                evolution = None
            
            self_model = self.self_model_engine.construct_self_model(
                user_id=user_id,
                identity_snapshot=snapshot,
                inferences=inferences,
                evidence=evidence
            )
            
            return {
                "identity": identity,
                "snapshot": snapshot,
                "self_model": self_model,
                "evolution": evolution
            }
            
        except Exception as e:
            logger.error(f"Identity construction failed: {str(e)}", exc_info=True)
            return {
                "identity": existing_identity,
                "snapshot": None,
                "self_model": None
            }
    
    async def _persist_all(self, user_id: str, result: V3PipelineResult):
        """Persist all pipeline outputs to database"""
        try:
            behavior_ids = []
            for bo in result.behavior_objects:
                bid = await self._upsert_behavior_object(user_id, bo)
                behavior_ids.append(bid)
            
            for ev in result.evidence:
                await self._insert_evidence(user_id, ev)

            # Inferences are the twin's CURRENT reasoning state (re-derived from
            # all behavior objects each run), not append-only events — so replace
            # the prior set instead of accumulating stale duplicates.
            if result.inferences:
                await execute("DELETE FROM inferences WHERE user_id = $1", user_id)
            for inf in result.inferences:
                await self._insert_inference(user_id, inf)
            
            if result.reflection:
                await self._insert_reflection(user_id, result.reflection)

            if result.identity:
                await self._upsert_identity(result.identity)

                # _upsert_identity adopts the stored identity_id when a row
                # for this user already exists. The snapshot was built earlier
                # in the run and still carries the id minted then, which is not
                # in the table - its foreign key fails, the failure is logged
                # and swallowed, and no snapshot is written for that ingest.
                #
                # IdentitySnapshot is frozen, which is the point of a snapshot,
                # so the reconciled id is passed to the insert rather than
                # assigned onto the model.
                persisted_identity_id = result.identity.identity_id

            # Snapshots are only persisted when identity shift crosses the
            # Eq.2 threshold (paper-faithful — avoids a snapshot row per
            # ingest). self_model has a FK to identity_snapshots, so when the
            # in-memory snapshot was NOT persisted this round, it must point
            # at the latest snapshot that actually exists in storage instead
            # (the identity truly hasn't shifted enough to warrant a new one).
            persisted_snapshot_id = None
            if result.snapshot:
                if result.snapshot.metadata.get("snapshot_threshold_exceeded", True):
                    if await self._insert_snapshot(result.snapshot,
                                                   identity_id=persisted_identity_id):
                        persisted_snapshot_id = result.snapshot.snapshot_id
                    else:
                        # The insert did not land. Pointing the self model at
                        # this id anyway would violate its foreign key, so fall
                        # back to whatever snapshot is actually stored.
                        row = await fetchrow(
                            "SELECT snapshot_id FROM identity_snapshots "
                            "WHERE identity_id = $1 ORDER BY created_at DESC LIMIT 1",
                            persisted_identity_id,
                        )
                        persisted_snapshot_id = row["snapshot_id"] if row else None
                else:
                    row = await fetchrow(
                        "SELECT snapshot_id FROM identity_snapshots "
                        "WHERE identity_id = $1 ORDER BY created_at DESC LIMIT 1",
                        persisted_identity_id,
                    )
                    persisted_snapshot_id = row["snapshot_id"] if row else None

            if result.self_model:
                if persisted_snapshot_id:
                    result.self_model.identity_snapshot_id = persisted_snapshot_id
                    await self._upsert_self_model(result.self_model)
                else:
                    logger.warning(
                        "Skipping self_model upsert: no persisted snapshot exists yet for identity %s",
                        result.snapshot.identity_id if result.snapshot else "?",
                    )
            
            logger.info(f"Persisted pipeline results for user {user_id}")
            
        except Exception as e:
            logger.error(f"Persistence failed: {str(e)}", exc_info=True)
    
    async def _upsert_behavior_object(self, user_id: str, bo: BehaviorObject) -> Optional[int]:
        """Insert or update a behavior object in the database"""
        try:
            existing = await fetchrow(
                "SELECT id FROM behavior_objects WHERE unique_id = $1",
                bo.unique_id
            )
            
            if existing:
                await execute(
                    """
                    UPDATE behavior_objects SET
                        topic = $1, subtopics = $2, keywords = $3,
                        creators = $4, creator_diversity_score = $5,
                        engagement_statistics = $6::jsonb,
                        watch_statistics = $7::jsonb,
                        temporal_statistics = $8::jsonb,
                        trend_information = $9::jsonb,
                        lifecycle_state = $10,
                        importance_score = $11, confidence_score = $12,
                        stability_score = $13, evidence_references = $14::jsonb,
                        supporting_event_ids = $15::jsonb,
                        version = $16, metadata = $17::jsonb,
                        tags = $18::jsonb, updated_at = NOW()
                    WHERE unique_id = $19
                    """,
                    bo.topic,
                    json.dumps(bo.subtopics),
                    json.dumps(bo.keywords),
                    json.dumps(bo.creators),
                    bo.creator_diversity_score,
                    json.dumps(bo.engagement_statistics.dict(), default=str),
                    json.dumps(bo.watch_statistics.dict(), default=str),
                    json.dumps(bo.temporal_statistics.dict(), default=str),
                    json.dumps(bo.trend_information.dict(), default=str),
                    bo.lifecycle_state.value,
                    bo.importance_score,
                    bo.confidence_score,
                    bo.stability_score,
                    json.dumps(bo.evidence_references),
                    json.dumps(bo.supporting_event_ids),
                    bo.version,
                    json.dumps(bo.metadata, default=str),
                    json.dumps(bo.tags),
                    bo.unique_id
                )
                return existing["id"]
            else:
                row = await fetchrow(
                    """
                    INSERT INTO behavior_objects (
                        unique_id, user_id, topic, subtopics, keywords,
                        creators, creator_diversity_score,
                        engagement_statistics, watch_statistics,
                        temporal_statistics, trend_information,
                        lifecycle_state, importance_score, confidence_score,
                        stability_score, evidence_references,
                        supporting_event_ids, supporting_cluster_ids,
                        version, metadata, tags,
                        created_at, updated_at
                    ) VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,
                        $6::jsonb,$7,
                        $8::jsonb,$9::jsonb,
                        $10::jsonb,$11::jsonb,
                        $12,$13,$14,
                        $15,$16::jsonb,
                        $17::jsonb,$18::jsonb,
                        $19,$20::jsonb,$21::jsonb,
                        $22,$23)
                    RETURNING id
                    """,
                    bo.unique_id, user_id, bo.topic,
                    json.dumps(bo.subtopics),
                    json.dumps(bo.keywords),
                    json.dumps(bo.creators),
                    bo.creator_diversity_score,
                    json.dumps(bo.engagement_statistics.dict(), default=str),
                    json.dumps(bo.watch_statistics.dict(), default=str),
                    json.dumps(bo.temporal_statistics.dict(), default=str),
                    json.dumps(bo.trend_information.dict(), default=str),
                    bo.lifecycle_state.value,
                    bo.importance_score, bo.confidence_score,
                    bo.stability_score,
                    json.dumps(bo.evidence_references),
                    json.dumps(bo.supporting_event_ids),
                    json.dumps(bo.supporting_cluster_ids),
                    bo.version,
                    json.dumps(bo.metadata, default=str),
                    json.dumps(bo.tags),
                    bo.created_at, bo.updated_at
                )
                return row["id"] if row else None
                
        except Exception as e:
            logger.error(f"Error upserting behavior object: {str(e)}", exc_info=True)
            return None
    
    async def _insert_evidence(self, user_id: str, ev: Evidence):
        """Insert evidence into database"""
        try:
            await execute(
                """
                INSERT INTO evidence (
                    evidence_id, user_id, evidence_type,
                    supporting_events, supporting_clusters,
                    supporting_behavior_objects,
                    confidence, weight, counter_evidence_ids,
                    conflicting_observations, conflict_resolution,
                    net_confidence, explanation, key_metrics,
                    time_window_start, time_window_end, metadata
                ) VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,$6::jsonb,
                    $7,$8,$9::jsonb,$10::jsonb,$11,$12,$13,$14::jsonb,
                    $15,$16,$17::jsonb)
                ON CONFLICT (evidence_id) DO NOTHING
                """,
                ev.evidence_id, user_id, ev.evidence_type.value,
                json.dumps(ev.supporting_events, default=str),
                json.dumps(ev.supporting_clusters, default=str),
                json.dumps(ev.supporting_behavior_objects, default=str),
                ev.confidence, ev.weight,
                json.dumps(ev.counter_evidence_ids),
                json.dumps(ev.conflicting_observations),
                ev.conflict_resolution,
                ev.net_confidence, ev.explanation,
                json.dumps(ev.key_metrics),
                ev.time_window_start, ev.time_window_end,
                json.dumps(ev.metadata)
            )
        except Exception as e:
            logger.error(f"Error inserting evidence: {str(e)}", exc_info=True)
    
    async def _insert_inference(self, user_id: str, inf: Inference):
        """Insert inference into database"""
        try:
            await execute(
                """
                INSERT INTO inferences (
                    inference_id, user_id, inference_type,
                    label, description, confidence, importance, strength,
                    supporting_evidence, evidence_summary,
                    affected_topics, affected_creators, affected_behaviors,
                    recommendation_seed, suggested_actions,
                    inferred_at, valid_from, valid_until,
                    rule_name, context_id, metadata
                    -- claim_key is a GENERATED column (migration_v20): Postgres
                    -- derives it from rule_name + label, so it can never be
                    -- omitted or drift from the definition used to match
                    -- corrections. Do not add it here.
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,
                    $11::jsonb,$12::jsonb,$13::jsonb,$14,$15::jsonb,
                    $16,$17,$18,$19,$20,$21::jsonb)
                ON CONFLICT (inference_id) DO NOTHING
                """,
                inf.inference_id, user_id, inf.inference_type,
                inf.label, inf.description, inf.confidence,
                inf.importance, inf.strength,
                json.dumps(inf.supporting_evidence),
                inf.evidence_summary,
                json.dumps(inf.affected_topics),
                json.dumps(inf.affected_creators),
                json.dumps(inf.affected_behaviors),
                inf.recommendation_seed,
                json.dumps(inf.suggested_actions),
                inf.inferred_at, inf.valid_from, inf.valid_until,
                inf.rule_name, inf.context_id,
                json.dumps(inf.metadata),
            )
        except Exception as e:
            logger.error(f"Error inserting inference: {str(e)}", exc_info=True)
    
    async def _upsert_identity(self, identity: Identity):
        """Insert or update identity.

        Matched on user_id, not identity_id. The table is unique on both, one
        row per person, and the pipeline mints a fresh identity_id whenever it
        could not load the existing identity. Looking up by that fresh id found
        nothing, so this fell through to an INSERT which violated
        identities_user_id_key - and the error was swallowed here, leaving the
        identity silently frozen at its previous contents while every later
        snapshot failed its foreign key against an identity_id that was never
        stored. Observed on a live second ingest.

        The stored identity_id wins when a row already exists, because snapshots
        and traces already reference it; overwriting it would strand them.
        """
        try:
            existing = await fetchrow(
                "SELECT id, identity_id FROM identities WHERE user_id = $1",
                identity.user_id
            )

            if existing:
                # Downstream writes in this run reference this attribute, so it
                # has to name the row that actually exists.
                identity.identity_id = existing["identity_id"]
                await execute(
                    """
                    UPDATE identities SET
                        behavior_profile = $1::jsonb,
                        interest_graph = $2::jsonb,
                        creator_graph = $3::jsonb,
                        learning_style = $4::jsonb,
                        attention_profile = $5::jsonb,
                        exploration_profile = $6::jsonb,
                        consistency_profile = $7::jsonb,
                        habit_profile = $8::jsonb,
                        motivation_signals = $9::jsonb,
                        behavior_timeline = $10::jsonb,
                        dominant_topics = $11::jsonb,
                        emerging_topics = $12::jsonb,
                        declining_topics = $13::jsonb,
                        overall_confidence = $14,
                        identity_completeness = $15,
                        identity_version = $16,
                        source_behavior_objects = $17::jsonb,
                        source_inferences = $18::jsonb,
                        source_evidence = $19::jsonb,
                        metadata = $20::jsonb,
                        updated_at = NOW()
                    WHERE user_id = $21
                    """,
                    json.dumps(identity.behavior_profile.dict(), default=str),
                    json.dumps(identity.interest_graph.dict(), default=str),
                    json.dumps(identity.creator_graph.dict(), default=str),
                    json.dumps(identity.learning_style.dict(), default=str),
                    json.dumps(identity.attention_profile.dict(), default=str),
                    json.dumps(identity.exploration_profile.dict(), default=str),
                    json.dumps(identity.consistency_profile.dict(), default=str),
                    json.dumps(identity.habit_profile.dict(), default=str),
                    json.dumps(identity.motivation_signals.dict(), default=str),
                    json.dumps(identity.behavior_timeline),
                    json.dumps(identity.dominant_topics),
                    json.dumps(identity.emerging_topics),
                    json.dumps(identity.declining_topics),
                    identity.overall_confidence,
                    identity.identity_completeness,
                        identity.identity_version,
                    json.dumps(identity.source_behavior_objects),
                    json.dumps(identity.source_inferences),
                    json.dumps(identity.source_evidence, default=str),
                    # Persisted so identity_shift / snapshot_threshold_exceeded
                    # are inspectable in the database. They were computed and
                    # used at runtime but never stored, which is precisely why
                    # the snapshot gate's behaviour was invisible until someone
                    # noticed the snapshot count had stopped moving.
                    json.dumps(identity.metadata, default=str),
                    # $21: the WHERE now matches on user_id, the column
                    # the table is actually keyed by for one row per person.
                    identity.user_id
                )
            else:
                await execute(
                    """
                    INSERT INTO identities (
                        identity_id, user_id, behavior_profile,
                        interest_graph, creator_graph, learning_style,
                        attention_profile, exploration_profile,
                        consistency_profile, habit_profile,
                        motivation_signals, behavior_timeline,
                        dominant_topics, emerging_topics, declining_topics,
                        overall_confidence, identity_completeness,
                        identity_version, source_behavior_objects,
                        source_inferences, source_evidence, metadata
                    ) VALUES ($1,$2,$3::jsonb,$4::jsonb,$5::jsonb,
                        $6::jsonb,$7::jsonb,$8::jsonb,$9::jsonb,
                        $10::jsonb,$11::jsonb,$12::jsonb,
                        $13::jsonb,$14::jsonb,$15::jsonb,
                        $16,$17,$18,$19::jsonb,$20::jsonb,$21::jsonb,$22::jsonb)
                    """,
                    identity.identity_id, identity.user_id,
                    json.dumps(identity.behavior_profile.dict(), default=str),
                    json.dumps(identity.interest_graph.dict(), default=str),
                    json.dumps(identity.creator_graph.dict(), default=str),
                    json.dumps(identity.learning_style.dict(), default=str),
                    json.dumps(identity.attention_profile.dict(), default=str),
                    json.dumps(identity.exploration_profile.dict(), default=str),
                    json.dumps(identity.consistency_profile.dict(), default=str),
                    json.dumps(identity.habit_profile.dict(), default=str),
                    json.dumps(identity.motivation_signals.dict(), default=str),
                    json.dumps(identity.behavior_timeline),
                    json.dumps(identity.dominant_topics),
                    json.dumps(identity.emerging_topics),
                    json.dumps(identity.declining_topics),
                    identity.overall_confidence,
                    identity.identity_completeness,
                    identity.identity_version,
                    json.dumps(identity.source_behavior_objects),
                    json.dumps(identity.source_inferences),
                    json.dumps(identity.source_evidence),
                    json.dumps(identity.metadata, default=str)
                )
        except Exception as e:
            logger.error(f"Error upserting identity: {str(e)}", exc_info=True)
    
    async def _insert_reflection(self, user_id: str, ref: Reflection):
        try:
            await execute(
                """
                INSERT INTO reflections (
                    reflection_id, user_id, reflection_type,
                    period_start, period_end, summary,
                    key_insights, metrics, patterns_identified,
                    changes_detected, recommendations, confidence,
                    event_count, memory_refs, metadata
                ) VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,
                    $9::jsonb,$10::jsonb,$11::jsonb,$12,$13,
                    $14::jsonb,$15::jsonb)
                ON CONFLICT (reflection_id) DO NOTHING
                """,
                ref.reflection_id, user_id, ref.reflection_type,
                ref.period_start, ref.period_end, ref.summary,
                json.dumps(ref.key_insights),
                json.dumps(ref.metrics),
                json.dumps(ref.patterns_identified),
                json.dumps(ref.changes_detected),
                json.dumps(ref.recommendations),
                ref.confidence, ref.event_count,
                json.dumps(ref.memory_refs),
                json.dumps(ref.metadata),
            )
        except Exception as e:
            logger.error(f"Error inserting reflection: {str(e)}", exc_info=True)

    async def _load_baseline_snapshot(self, identity_id: str):
        """Latest persisted snapshot for an identity, plus its age in hours.

        Returns (snapshot_or_None, age_hours_or_None). Failures degrade to
        (None, None), which makes the caller force a snapshot — the safe
        direction, since writing one extra row is far cheaper than silently
        losing the identity's history.
        """
        try:
            row = await fetchrow(
                "SELECT snapshot_data, snapshot_timestamp FROM identity_snapshots "
                "WHERE identity_id = $1 ORDER BY snapshot_timestamp DESC LIMIT 1",
                identity_id,
            )
            if not row:
                return None, None

            raw = row["snapshot_data"]
            data = json.loads(raw) if isinstance(raw, str) else raw
            snapshot = IdentitySnapshot(**data) if data else None

            age_hours = None
            ts = row["snapshot_timestamp"]
            if ts is not None:
                now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.utcnow()
                age_hours = (now - ts).total_seconds() / 3600.0

            return snapshot, age_hours
        except Exception as e:
            logger.warning("Could not load baseline snapshot for %s: %s", identity_id, e)
            return None, None

    async def _insert_snapshot(self, snapshot: IdentitySnapshot,
                               identity_id: Optional[str] = None) -> bool:
        """Insert snapshot into database. True only if the row is now there.

        The caller sets self_model.identity_snapshot_id from this snapshot, and
        that column has a foreign key. Reporting success unconditionally meant a
        swallowed failure here produced a foreign-key violation one statement
        later, which was itself swallowed, so the self model silently stopped
        being written. Observed in a live run.
        """
        try:
            await execute(
                """
                INSERT INTO identity_snapshots (
                    snapshot_id, identity_id, identity_version,
                    user_id, snapshot_data, overall_confidence,
                    identity_completeness, dominant_topics,
                    emerging_topics, declining_topics,
                    is_active, valid_until, snapshot_timestamp
                ) VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8::jsonb,$9::jsonb,
                    $10::jsonb,$11,$12,$13)
                ON CONFLICT (snapshot_id) DO NOTHING
                """,
                snapshot.snapshot_id,
                # The identity row this belongs to, which may have been
                # reconciled to an existing one since the snapshot was built.
                identity_id or snapshot.identity_id,
                snapshot.identity_version,
                snapshot.user_id,
                json.dumps(snapshot.dict(), default=str),
                snapshot.overall_confidence,
                snapshot.identity_completeness,
                json.dumps(snapshot.dominant_topics),
                json.dumps(snapshot.emerging_topics),
                json.dumps(snapshot.declining_topics),
                snapshot.is_active,
                snapshot.valid_until,
                snapshot.snapshot_timestamp
            )
            # ON CONFLICT DO NOTHING above means a row with this id may have
            # existed already, which is equally fine for the caller: what it
            # needs to know is whether the id is now present.
            return bool(await fetchrow(
                "SELECT 1 FROM identity_snapshots WHERE snapshot_id = $1",
                snapshot.snapshot_id,
            ))
        except Exception as e:
            logger.error(f"Error inserting snapshot: {str(e)}", exc_info=True)
            return False
    
    async def _upsert_self_model(self, self_model: SelfModel):
        """Insert or update self model (one per user_id)"""
        try:
            beliefs_data = [b.dict() for b in self_model.beliefs]
            
            await execute(
                """
                INSERT INTO self_models (
                    self_model_id, user_id, identity_snapshot_id,
                    beliefs, strong_beliefs, uncertain_beliefs,
                    uncertainty_map, overall_confidence,
                    model_completeness
                ) VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,$6::jsonb,
                    $7::jsonb,$8,$9)
                ON CONFLICT (user_id) DO UPDATE SET
                    self_model_id = EXCLUDED.self_model_id,
                    identity_snapshot_id = EXCLUDED.identity_snapshot_id,
                    beliefs = EXCLUDED.beliefs,
                    strong_beliefs = EXCLUDED.strong_beliefs,
                    uncertain_beliefs = EXCLUDED.uncertain_beliefs,
                    uncertainty_map = EXCLUDED.uncertainty_map,
                    overall_confidence = EXCLUDED.overall_confidence,
                    model_completeness = EXCLUDED.model_completeness,
                    updated_at = NOW()
                """,
                self_model.self_model_id,
                self_model.user_id,
                self_model.identity_snapshot_id,
                json.dumps(beliefs_data, default=str),
                json.dumps(self_model.strong_beliefs, default=str),
                json.dumps(self_model.uncertain_beliefs, default=str),
                json.dumps(self_model.uncertainty_map.dict(), default=str),
                self_model.overall_confidence,
                self_model.model_completeness
            )
        except Exception as e:
            logger.error(f"Error upserting self model: {str(e)}", exc_info=True)
    
    async def _load_behavior_object_ids(self, user_id: str) -> List[str]:
        """Load existing behavior object IDs from database"""
        try:
            rows = await fetch(
                "SELECT unique_id FROM behavior_objects WHERE user_id = $1",
                user_id
            )
            return [r["unique_id"] for r in rows]
        except Exception:
            return []
    
    async def _load_behavior_objects(self, user_id: str) -> List[BehaviorObject]:
        """Load existing behavior objects from database"""
        try:
            rows = await fetch(
                "SELECT * FROM behavior_objects WHERE user_id = $1 ORDER BY updated_at DESC",
                user_id
            )
            objects = []
            for row in rows:
                try:
                    import json
                    engagement = json.loads(row["engagement_statistics"]) if isinstance(row["engagement_statistics"], str) else row["engagement_statistics"]
                    watch = json.loads(row["watch_statistics"]) if isinstance(row["watch_statistics"], str) else row["watch_statistics"]
                    temporal = json.loads(row["temporal_statistics"]) if isinstance(row["temporal_statistics"], str) else row["temporal_statistics"]
                    trend = json.loads(row["trend_information"]) if isinstance(row["trend_information"], str) else row["trend_information"]
                    
                    subtopics = json.loads(row["subtopics"]) if isinstance(row["subtopics"], str) else (row["subtopics"] or [])
                    keywords = json.loads(row["keywords"]) if isinstance(row["keywords"], str) else (row["keywords"] or [])
                    creators = json.loads(row["creators"]) if isinstance(row["creators"], str) else (row["creators"] or [])
                    evidence_refs = json.loads(row["evidence_references"]) if isinstance(row["evidence_references"], str) else (row["evidence_references"] or [])
                    event_ids = json.loads(row["supporting_event_ids"]) if isinstance(row["supporting_event_ids"], str) else (row["supporting_event_ids"] or [])
                    cluster_ids = json.loads(row["supporting_cluster_ids"]) if isinstance(row["supporting_cluster_ids"], str) else (row["supporting_cluster_ids"] or [])
                    metadata = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
                    tags = json.loads(row["tags"]) if isinstance(row["tags"], str) else (row["tags"] or [])
                    evolution = json.loads(row["evolution_history"]) if isinstance(row["evolution_history"], str) else (row["evolution_history"] or [])
                    
                    from backend.reasoning.behavior_object import (
                        BehaviorObject, EngagementStatistics, WatchStatistics,
                        TemporalStatistics, TrendInformation, BehaviorLifecycleState,
                        EvolutionSnapshot
                    )
                    
                    def _to_naive(dt):
                        if isinstance(dt, datetime) and dt.tzinfo is not None:
                            return dt.replace(tzinfo=None)
                        return dt

                    bo = BehaviorObject(
                        unique_id=row["unique_id"],
                        topic=row["topic"],
                        subtopics=subtopics,
                        representative_embedding=row.get("representative_embedding") or [0.0] * 384,
                        keywords=keywords,
                        creators=creators,
                        creator_diversity_score=float(row.get("creator_diversity_score", 0) or 0),
                        engagement_statistics=EngagementStatistics(**engagement if engagement else {
                            "total_interactions": 0, "like_rate": 0, "save_rate": 0,
                            "share_rate": 0, "comment_rate": 0,
                            "overall_engagement_rate": 0, "engagement_quality_score": 0
                        }),
                        watch_statistics=WatchStatistics(**watch if watch else {
                            "total_watch_time": 0, "avg_watch_time": 0, "median_watch_time": 0,
                            "max_watch_time": 0, "min_watch_time": 0, "watch_time_std": 0,
                            "completion_rate": 0
                        }),
                        temporal_statistics=TemporalStatistics(**temporal if temporal else {
                            "first_seen": datetime.utcnow(), "last_seen": datetime.utcnow(),
                            "days_active": 0, "occurrence_count": 0, "daily_frequency": 0,
                            "weekly_frequency": 0, "recency_score": 0, "consistency_score": 0
                        }),
                        trend_information=TrendInformation(**trend if trend else {
                            "trend_direction": "stable", "growth_rate": 0, "momentum_score": 0,
                            "volatility_score": 0, "prediction_confidence": 0,
                            "expected_trajectory": "unknown"
                        }),
                        lifecycle_state=BehaviorLifecycleState(row.get("lifecycle_state", "emerging")),
                        importance_score=float(row.get("importance_score", 0) or 0),
                        confidence_score=float(row.get("confidence_score", 0) or 0),
                        stability_score=float(row.get("stability_score", 0) or 0),
                        evidence_references=evidence_refs,
                        supporting_event_ids=event_ids,
                        supporting_cluster_ids=cluster_ids,
                        evolution_history=evolution,
                        version=row.get("version", 1) or 1,
                        created_at=_to_naive(row["created_at"]),
                        updated_at=_to_naive(row["updated_at"]),
                        last_accessed=_to_naive(row.get("last_accessed")),
                        access_count=row.get("access_count", 0) or 0,
                        metadata=metadata,
                        tags=tags
                    )
                    objects.append(bo)
                except Exception as e:
                    logger.warning(f"Error loading behavior object {row.get('unique_id')}: {e}")
                    continue
            
            return objects
            
        except Exception as e:
            logger.error(f"Error loading behavior objects: {str(e)}", exc_info=True)
            return []

    async def _load_all_evidence(self, user_id: str, exclude_ids: Optional[set] = None) -> List[Evidence]:
        """Load all previously-collected evidence for a user (for identity
        confidence, which must reflect the full accumulated picture, not just
        the current ingest batch)."""
        exclude_ids = exclude_ids or set()
        try:
            rows = await fetch(
                "SELECT * FROM evidence WHERE user_id = $1 ORDER BY created_at DESC LIMIT 500",
                user_id,
            )
            items: List[Evidence] = []
            for row in rows:
                if row["evidence_id"] in exclude_ids:
                    continue
                try:
                    def _j(key, default):
                        v = row.get(key)
                        if isinstance(v, str):
                            try:
                                return json.loads(v)
                            except Exception:
                                return default
                        return v if v is not None else default

                    items.append(Evidence(
                        evidence_id=row["evidence_id"],
                        evidence_type=row["evidence_type"],
                        supporting_events=_j("supporting_events", []),
                        supporting_clusters=_j("supporting_clusters", []),
                        supporting_behavior_objects=_j("supporting_behavior_objects", []),
                        confidence=float(row["confidence"] or 0),
                        weight=float(row["weight"] or 0),
                        counter_evidence_ids=_j("counter_evidence_ids", []),
                        conflicting_observations=_j("conflicting_observations", []),
                        conflict_resolution=row.get("conflict_resolution"),
                        net_confidence=row.get("net_confidence"),
                        explanation=row["explanation"] or "",
                        key_metrics=_j("key_metrics", {}),
                        time_window_start=row["time_window_start"] or row["created_at"],
                        time_window_end=row["time_window_end"] or row["created_at"],
                        created_at=row["created_at"],
                        metadata=_j("metadata", {}),
                    ))
                except Exception as e:
                    logger.warning(f"Error loading evidence {row.get('evidence_id')}: {e}")
                    continue
            return items
        except Exception as e:
            logger.error(f"Error loading evidence: {str(e)}", exc_info=True)
            return []

    async def load_identity(self, user_id: str) -> Optional[Identity]:
        """Load identity from database"""
        try:
            row = await fetchrow(
                "SELECT * FROM identities WHERE user_id = $1",
                user_id
            )
            if not row:
                return None
            
            import json
            bp_data = json.loads(row["behavior_profile"]) if isinstance(row["behavior_profile"], str) else (row["behavior_profile"] or {})
            ig_data = json.loads(row["interest_graph"]) if isinstance(row["interest_graph"], str) else (row["interest_graph"] or {})
            cg_data = json.loads(row["creator_graph"]) if isinstance(row["creator_graph"], str) else (row["creator_graph"] or {})
            ls_data = json.loads(row["learning_style"]) if isinstance(row["learning_style"], str) else (row["learning_style"] or {})
            ap_data = json.loads(row["attention_profile"]) if isinstance(row["attention_profile"], str) else (row["attention_profile"] or {})
            ep_data = json.loads(row["exploration_profile"]) if isinstance(row["exploration_profile"], str) else (row["exploration_profile"] or {})
            cp_data = json.loads(row["consistency_profile"]) if isinstance(row["consistency_profile"], str) else (row["consistency_profile"] or {})
            hp_data = json.loads(row["habit_profile"]) if isinstance(row["habit_profile"], str) else (row["habit_profile"] or {})
            ms_data = json.loads(row["motivation_signals"]) if isinstance(row["motivation_signals"], str) else (row["motivation_signals"] or {})
            
            from backend.identity.identity_engine import (
                Identity, BehaviorProfile, InterestGraph, CreatorGraph,
                LearningStyle, AttentionProfile, ExplorationProfile,
                ConsistencyProfile, HabitProfile, MotivationSignals
            )
            
            def _to_naive(dt):
                if isinstance(dt, datetime) and dt.tzinfo is not None:
                    return dt.replace(tzinfo=None)
                return dt

            identity = Identity(
                identity_id=row["identity_id"],
                user_id=row["user_id"],
                behavior_profile=BehaviorProfile(**bp_data),
                interest_graph=InterestGraph(**ig_data),
                creator_graph=CreatorGraph(**cg_data),
                learning_style=LearningStyle(**ls_data),
                attention_profile=AttentionProfile(**ap_data),
                exploration_profile=ExplorationProfile(**ep_data),
                consistency_profile=ConsistencyProfile(**cp_data),
                habit_profile=HabitProfile(**hp_data),
                motivation_signals=MotivationSignals(**ms_data),
                behavior_timeline=json.loads(row["behavior_timeline"]) if isinstance(row["behavior_timeline"], str) else (row["behavior_timeline"] or []),
                dominant_topics=json.loads(row["dominant_topics"]) if isinstance(row["dominant_topics"], str) else (row["dominant_topics"] or []),
                emerging_topics=json.loads(row["emerging_topics"]) if isinstance(row["emerging_topics"], str) else (row["emerging_topics"] or []),
                declining_topics=json.loads(row["declining_topics"]) if isinstance(row["declining_topics"], str) else (row["declining_topics"] or []),
                overall_confidence=float(row.get("overall_confidence", 0) or 0),
                identity_completeness=float(row.get("identity_completeness", 0) or 0),
                identity_version=row.get("identity_version", 1) or 1,
                created_at=_to_naive(row["created_at"]),
                updated_at=_to_naive(row["updated_at"]),
                source_behavior_objects=json.loads(row["source_behavior_objects"]) if isinstance(row["source_behavior_objects"], str) else (row["source_behavior_objects"] or []),
                source_inferences=json.loads(row["source_inferences"]) if isinstance(row["source_inferences"], str) else (row["source_inferences"] or []),
                source_evidence=json.loads(row["source_evidence"]) if isinstance(row["source_evidence"], str) else (row["source_evidence"] or []),
                long_term_preferences=json.loads(row["long_term_preferences"]) if isinstance(row["long_term_preferences"], str) else (row["long_term_preferences"] or {})
            )
            return identity
            
        except Exception as e:
            logger.error(f"Error loading identity: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def _lifecycle_for(stats) -> str:
        """State from the behaviour's own statistics rather than from the batch.

        This replaced a thresholding of cluster.growth_rate, which is
        occurrence_count over days elapsed: a positive frequency averaging 3.08
        on real data, so "> 0.5" caught 217 of 226 objects, and DECLINING,
        which tested for a negative value, could not occur at all. See
        reasoning/lifecycle.py.
        """
        from backend.reasoning.lifecycle import evaluate_lifecycle

        temporal = stats["temporal"]
        trend = stats["trend"]
        state, _reason = evaluate_lifecycle(
            temporal if isinstance(temporal, dict) else temporal.dict(),
            trend if isinstance(trend, dict) else trend.dict(),
        )
        return state

    async def _refresh_lifecycles(self, user_id: str) -> int:
        """Re-evaluate every one of this user's behaviours, not just this batch.

        This part was missing rather than wrong. State was written only when a
        topic appeared in an ingest, and a topic someone has abandoned never
        appears in one again, so the single code path that could mark it dormant
        was unreachable for exactly the behaviours that needed it. Ninety-six
        objects unseen for over thirty days were still labelled growing, the
        oldest last seen 600 days earlier.

        Sweeping all of them on every ingest costs two queries per user and
        makes the stored state a statement about now rather than about whenever
        the topic was last mentioned.
        """
        from backend.reasoning.lifecycle import evaluate_lifecycle, recent_share

        try:
            rows = await fetch(
                """SELECT unique_id, temporal_statistics, trend_information,
                          supporting_event_ids, lifecycle_state
                   FROM behavior_objects WHERE user_id = $1""",
                user_id,
            )
            if not rows:
                return 0

            def _load(value):
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except (ValueError, TypeError):
                        return {}
                return value or {}

            # One query for every event across every behaviour, rather than one
            # query per behaviour.
            wanted = set()
            per_object = {}
            for row in rows:
                ids = []
                for raw in (_load(row["supporting_event_ids"]) or []):
                    try:
                        ids.append(int(raw))
                    except (TypeError, ValueError):
                        continue
                per_object[row["unique_id"]] = ids
                wanted.update(ids)

            stamps = {}
            if wanted:
                ordered = sorted(wanted)
                placeholders = ", ".join(f"${i + 2}" for i in range(len(ordered)))
                for ev in await fetch(
                    f"""SELECT id, timestamp FROM events
                        WHERE user_id = $1 AND id IN ({placeholders})""",
                    user_id, *ordered,
                ):
                    stamps[ev["id"]] = ev["timestamp"]

            changed = 0
            for row in rows:
                temporal = _load(row["temporal_statistics"])
                trend = _load(row["trend_information"])

                times = [stamps[i] for i in per_object[row["unique_id"]] if i in stamps]
                share = recent_share(times)
                if share is not None:
                    trend["recent_share"] = share

                state, _reason = evaluate_lifecycle(temporal, trend)
                if state == row["lifecycle_state"] and share is None:
                    continue

                await execute(
                    """UPDATE behavior_objects
                       SET lifecycle_state = $1, trend_information = $2::jsonb,
                           updated_at = NOW()
                       WHERE unique_id = $3""",
                    state, json.dumps(trend, default=str), row["unique_id"],
                )
                if state != row["lifecycle_state"]:
                    changed += 1

            if changed:
                logger.info("Lifecycle refresh: %d behaviours changed state for %s",
                            changed, user_id)
            return changed

        except Exception as e:
            logger.error("Lifecycle refresh failed for %s: %s", user_id, e,
                         exc_info=True)
            return 0
    
    @staticmethod
    def _cluster_to_engagement(cluster):
        """Convert cluster metrics to engagement/watch/temporal/trend dicts"""
        from datetime import datetime, timezone
        # cluster.last_seen is timezone-aware (inherited from event.timestamp)
        now = datetime.now(timezone.utc)
        days_span = max(1, (cluster.last_seen - cluster.first_seen).days)
        
        return {
            "engagement": {
                "total_interactions": cluster.occurrence_count,
                "like_rate": cluster.engagement_rate,
                "save_rate": cluster.engagement_rate * 0.5,
                "share_rate": cluster.engagement_rate * 0.2,
                "comment_rate": cluster.engagement_rate * 0.1,
                "overall_engagement_rate": cluster.engagement_rate,
                "engagement_quality_score": cluster.engagement_rate * 0.8
            },
            "watch": {
                "total_watch_time": cluster.avg_watch_time * cluster.occurrence_count,
                "avg_watch_time": cluster.avg_watch_time,
                "median_watch_time": cluster.avg_watch_time,
                "max_watch_time": cluster.avg_watch_time * 2,
                "min_watch_time": cluster.avg_watch_time * 0.3,
                "watch_time_std": cluster.avg_watch_time * 0.4,
                "completion_rate": min(1.0, cluster.avg_watch_time / 30.0)
            },
            "temporal": {
                "first_seen": cluster.first_seen.isoformat(),
                "last_seen": cluster.last_seen.isoformat(),
                "days_active": days_span,
                "occurrence_count": cluster.occurrence_count,
                "daily_frequency": cluster.occurrence_count / days_span,
                "weekly_frequency": cluster.occurrence_count / max(1, days_span // 7),
                # Clamped at BOTH ends. timedelta.days floors toward negative
                # infinity, so a last_seen even seconds in the future gives
                # -1 and this returns 1.0333 — outside BehaviorObject's
                # ge=0/le=1 bound, which made construction raise and (see
                # _consolidate_events) discarded every behaviour object for
                # the run. Future timestamps are not hypothetical: clock skew
                # on a client produces them, and /seed did.
                "recency_score": min(1.0, max(0.0, 1.0 - (now - cluster.last_seen).days / 30.0)),
                "consistency_score": min(1.0, cluster.occurrence_count / STABILITY_SATURATION_COUNT)
            },
            "trend": {
                # trend_direction is derived from lifecycle_state rather than
                # from growth_rate. growth_rate is occurrence_count over days
                # elapsed - a positive frequency averaging 3.08 on real data -
                # so thresholding it at 0.5 labelled 217 of 226 behaviours
                # "growing", including ones last seen 600 days earlier. The
                # enum itself is marked deprecated in favour of
                # BehaviorLifecycleState; this keeps the two from disagreeing
                # while anything still reads it.
                "trend_direction": _trend_direction_for(cluster),
                "growth_rate": cluster.growth_rate,
                "momentum_score": min(1.0, cluster.growth_rate),
                "volatility_score": 1.0 - cluster.temporal_weight,
                "prediction_confidence": cluster.confidence,
                "expected_trajectory": "unknown"
            }
        }
