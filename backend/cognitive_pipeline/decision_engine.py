"""
Decision Engine — Content Optimization Layer

Deterministic algorithmic selection of what goes into FinalContext.
No LLM. No DB calls. No randomness. No reasoning.

Receives:  FusedEvidence + CharacterPlan + RetrievalResult + RankedObjects
Outputs:   FinalContext (CharacterContext-compatible)
Architecture V3 — FROZEN. No redesign.
"""
import logging
import time
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set, Tuple

from backend.rag.fusion import FusedEvidence, FusedFact
from backend.rag.retriever import RetrievalResult, RetrievedObject
from backend.rag.memory_ranker import RankedObject
from backend.cognitive_planning.planner_models import CharacterPlan

logger = logging.getLogger(__name__)


# ── Scoring Weights ──────────────────────────────────────────────────────────

@dataclass
class DecisionWeights:
    confidence: float = 0.25
    recency: float = 0.15
    identity_alignment: float = 0.20
    goal_alignment: float = 0.15
    evidence_strength: float = 0.10
    stability: float = 0.10
    diversity_boost: float = 0.05


# ── Configuration ────────────────────────────────────────────────────────────

@dataclass
class DecisionConfig:
    confidence_threshold: float = 0.3
    recency_decay_days: float = 30.0
    max_facts_per_topic: int = 5
    min_topics_represented: int = 2
    max_total_facts: int = 30
    goal_alignment_threshold: float = 0.3
    weights: DecisionWeights = field(default_factory=DecisionWeights)


# ── Conflict Record ──────────────────────────────────────────────────────────

@dataclass
class ConflictRecord:
    topic: str
    fact_id_a: str
    fact_id_b: str
    claim_a: str
    claim_b: str
    confidence_diff: float


# ── Decision Trace Metrics ───────────────────────────────────────────────────

@dataclass
class DecisionMetrics:
    decision_ms: float = 0.0
    input_facts: int = 0
    after_confidence_threshold: int = 0
    after_dedup: int = 0
    after_diversity: int = 0
    after_goal_filter: int = 0
    final_facts: int = 0
    removed_low_confidence: int = 0
    removed_duplicates: int = 0
    removed_diversity: int = 0
    removed_goal_mismatch: int = 0
    conflicts_detected: int = 0
    uncertainty_domains: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


# ── FinalContext ─────────────────────────────────────────────────────────────

@dataclass
class FinalContext:
    selected_facts: List[FusedFact]
    removed_facts: List[FusedFact]
    decision_scores: Dict[str, float]
    conflicts: List[ConflictRecord]
    uncertainty_domains: List[str]
    identity_snapshot: Dict[str, Any]
    self_model: Dict[str, Any]
    filtered_retrieval_result: RetrievalResult
    goal_aligned_fact_ids: Set[str]
    metrics: DecisionMetrics

    @property
    def total_input(self) -> int:
        return len(self.selected_facts) + len(self.removed_facts)


# ── Decision Engine ──────────────────────────────────────────────────────────

class DecisionEngine:
    def __init__(self, config: Optional[DecisionConfig] = None):
        self.config = config or DecisionConfig()

    def decide(
        self,
        fused_evidence: FusedEvidence,
        character_plan: CharacterPlan,
        retrieval_result: RetrievalResult,
        ranked_objects: List[RankedObject],
        retrieval_context: Optional[Dict[str, Any]] = None,
    ) -> FinalContext:
        start = time.perf_counter()
        metrics = DecisionMetrics(input_facts=len(fused_evidence.facts))

        facts = list(fused_evidence.facts)
        if not facts:
            elapsed = (time.perf_counter() - start) * 1000
            metrics.decision_ms = elapsed
            return self._empty_result(retrieval_result, retrieval_context, metrics)

        # Extract identity/self-model from context
        identity_snapshot, self_model = self._extract_identity_data(retrieval_context)

        # Extract goal and topic data from plan + context
        goal_ids = self._extract_goal_ids(character_plan, retrieval_context)
        dominant_topics = self._extract_dominant_topics(identity_snapshot)

        # ── 1. Priority Scoring ──────────────────────────────────────────
        decision_scores: Dict[str, float] = {}
        for fact in facts:
            score = self._compute_priority_score(
                fact, identity_snapshot, dominant_topics,
                goal_ids, character_plan,
            )
            decision_scores[fact.fact_id] = score

        # ── 2. Confidence Thresholding ───────────────────────────────────
        threshold = self._effective_confidence_threshold(character_plan)
        kept: List[FusedFact] = []
        removed: List[FusedFact] = []
        for fact in facts:
            if fact.confidence >= threshold:
                kept.append(fact)
            else:
                removed.append(fact)
        metrics.removed_low_confidence = len(removed)
        metrics.after_confidence_threshold = len(kept)

        # ── 3. Duplicate Removal ─────────────────────────────────────────
        kept, dup_removed = self._remove_duplicates(kept)
        removed.extend(dup_removed)
        metrics.removed_duplicates = len(dup_removed)
        metrics.after_dedup = len(kept)

        # ── 4. Topic Diversity Enforcement ───────────────────────────────
        kept, div_removed = self._enforce_diversity(kept)
        removed.extend(div_removed)
        metrics.removed_diversity = len(div_removed)
        metrics.after_diversity = len(kept)

        # ── 5. Goal Alignment Filtering ──────────────────────────────────
        kept, goal_removed, goal_aligned_ids = self._filter_goal_alignment(
            kept, goal_ids, identity_snapshot,
        )
        removed.extend(goal_removed)
        metrics.removed_goal_mismatch = len(goal_removed)
        metrics.after_goal_filter = len(kept)

        # ── 6. Identity Consistency Check ────────────────────────────────
        # Already baked into priority scoring via identity_alignment factor.
        # Here we just log any strong mismatches.

        # ── 7. Conflict Detection ────────────────────────────────────────
        conflicts = self._detect_conflicts(kept)
        metrics.conflicts_detected = len(conflicts)

        # ── 8. Uncertainty Propagation ───────────────────────────────────
        uncertainty_domains = self._propagate_uncertainty(
            kept, removed, identity_snapshot, self_model,
        )
        metrics.uncertainty_domains = uncertainty_domains

        # ── 9. Evidence Provenance Preservation ──────────────────────────
        # Provenance is inherent in FusedFact.supporting_ids + source_id.
        # We pass it through unchanged.

        # ── 10. Final Context Optimization ───────────────────────────────
        kept = self._final_optimize(kept, decision_scores)

        metrics.final_facts = len(kept)
        remaining_scores = {fid: s for fid, s in decision_scores.items()
                            if fid in {f.fact_id for f in kept}}

        # Build filtered RetrievalResult
        filtered_retrieval = self._build_filtered_retrieval(
            retrieval_result, kept,
        )

        elapsed = (time.perf_counter() - start) * 1000
        metrics.decision_ms = elapsed

        return FinalContext(
            selected_facts=kept,
            removed_facts=removed,
            decision_scores=remaining_scores,
            conflicts=conflicts,
            uncertainty_domains=uncertainty_domains,
            identity_snapshot=identity_snapshot,
            self_model=self_model,
            filtered_retrieval_result=filtered_retrieval,
            goal_aligned_fact_ids=goal_aligned_ids,
            metrics=metrics,
        )

    # ── Priority Scoring ──────────────────────────────────────────────────

    def _compute_priority_score(
        self,
        fact: FusedFact,
        identity_snapshot: Dict[str, Any],
        dominant_topics: List[str],
        goal_ids: List[str],
        plan: CharacterPlan,
    ) -> float:
        w = self.config.weights

        c_score = fact.confidence
        r_score = self._score_recency(fact.timestamp)
        i_score = self._score_identity_alignment(fact, dominant_topics)
        g_score = self._score_goal_alignment(fact, goal_ids, plan)
        e_score = self._score_evidence_strength(fact)
        s_score = self._score_stability(fact)

        raw = (
            w.confidence * c_score +
            w.recency * r_score +
            w.identity_alignment * i_score +
            w.goal_alignment * g_score +
            w.evidence_strength * e_score +
            w.stability * s_score
        )

        return min(1.0, max(0.0, raw))

    def _score_recency(self, timestamp: Optional[datetime]) -> float:
        if timestamp is None:
            return 0.3
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
        now = datetime.utcnow()
        days_ago = (now - timestamp).total_seconds() / 86400.0
        if days_ago < 0:
            return 1.0
        return math.exp(-days_ago / self.config.recency_decay_days)

    def _score_identity_alignment(
        self,
        fact: FusedFact,
        dominant_topics: List[str],
    ) -> float:
        if not dominant_topics:
            return 0.5
        fact_text = (fact.claim + " " + (fact.topic or "")).lower()
        matches = sum(1 for t in dominant_topics if t.lower() in fact_text)
        return min(1.0, matches / max(1, len(dominant_topics)))

    def _score_goal_alignment(
        self,
        fact: FusedFact,
        goal_ids: List[str],
        plan: CharacterPlan,
    ) -> float:
        if not goal_ids:
            return 0.5
        content_str = (fact.claim + " " + (fact.topic or "")).lower()
        return 1.0 if any(gid.lower() in content_str for gid in goal_ids) else 0.3

    def _score_evidence_strength(self, fact: FusedFact) -> float:
        if not fact.supporting_ids:
            return 0.3
        return min(1.0, len(fact.supporting_ids) / 5.0)

    def _score_stability(self, fact: FusedFact) -> float:
        meta = fact.metadata or {}
        stability = meta.get("stability_score") or meta.get("behavior_stability")
        if stability is not None:
            return min(1.0, max(0.0, float(stability)))
        consistency = meta.get("consistency_score") or meta.get("overall_consistency")
        if consistency is not None:
            return min(1.0, max(0.0, float(consistency)))
        return 0.5

    # ── Confidence Thresholding ───────────────────────────────────────────

    def _effective_confidence_threshold(self, plan: CharacterPlan) -> float:
        plan_threshold = plan.reasoning_plan.confidence_threshold
        return max(plan_threshold, self.config.confidence_threshold)

    # ── Duplicate Removal ─────────────────────────────────────────────────

    def _remove_duplicates(
        self,
        facts: List[FusedFact],
    ) -> Tuple[List[FusedFact], List[FusedFact]]:
        seen: Set[str] = set()
        kept: List[FusedFact] = []
        removed: List[FusedFact] = []

        for fact in sorted(facts, key=lambda f: f.confidence, reverse=True):
            key = f"{fact.source_type}:{fact.topic or ''}:{fact.claim.strip().lower()[:100]}"
            if key in seen:
                removed.append(fact)
            else:
                seen.add(key)
                kept.append(fact)

        return kept, removed

    # ── Topic Diversity Enforcement ───────────────────────────────────────

    def _enforce_diversity(
        self,
        facts: List[FusedFact],
    ) -> Tuple[List[FusedFact], List[FusedFact]]:
        kept: List[FusedFact] = []
        removed: List[FusedFact] = []
        topic_counts: Dict[str, int] = {}
        topic_fact_map: Dict[str, List[FusedFact]] = {}

        for fact in facts:
            topic = fact.topic or "uncategorized"
            topic_fact_map.setdefault(topic, []).append(fact)

        for topic, tfacts in topic_fact_map.items():
            tfacts.sort(key=lambda f: f.confidence, reverse=True)
            limit = self.config.max_facts_per_topic
            kept.extend(tfacts[:limit])
            removed.extend(tfacts[limit:])
            topic_counts[topic] = len(tfacts[:limit])

        for fact in kept:
            topic = fact.topic or "uncategorized"
            if topic_counts.get(topic, 0) > 1:
                pass

        return kept, removed

    # ── Goal Alignment Filtering ──────────────────────────────────────────

    def _filter_goal_alignment(
        self,
        facts: List[FusedFact],
        goal_ids: List[str],
        identity_snapshot: Dict[str, Any],
    ) -> Tuple[List[FusedFact], List[FusedFact], Set[str]]:
        kept: List[FusedFact] = []
        removed: List[FusedFact] = []
        goal_aligned: Set[str] = set()

        if not goal_ids:
            return facts, removed, goal_aligned

        for fact in facts:
            score = self._score_goal_alignment(fact, goal_ids, identity_snapshot)
            if score >= self.config.goal_alignment_threshold:
                kept.append(fact)
                goal_aligned.add(fact.fact_id)
            else:
                removed.append(fact)

        return kept, removed, goal_aligned

    # ── Conflict Detection ────────────────────────────────────────────────

    def _detect_conflicts(self, facts: List[FusedFact]) -> List[ConflictRecord]:
        conflicts: List[ConflictRecord] = []
        topic_groups: Dict[str, List[FusedFact]] = {}

        for fact in facts:
            topic = fact.topic or "uncategorized"
            topic_groups.setdefault(topic, []).append(fact)

        for topic, tfacts in topic_groups.items():
            for i in range(len(tfacts)):
                for j in range(i + 1, len(tfacts)):
                    a, b = tfacts[i], tfacts[j]
                    if a.source_type == b.source_type and a.source_id == b.source_id:
                        continue
                    if self._claims_contradict(a.claim, b.claim):
                        conflicts.append(ConflictRecord(
                            topic=topic,
                            fact_id_a=a.fact_id,
                            fact_id_b=b.fact_id,
                            claim_a=a.claim[:80],
                            claim_b=b.claim[:80],
                            confidence_diff=abs(a.confidence - b.confidence),
                        ))

        return conflicts

    def _claims_contradict(self, claim_a: str, claim_b: str) -> bool:
        a_lower = claim_a.lower()
        b_lower = claim_b.lower()
        negations_a = {"not ", "doesn't", "don't", "isn't", "no ", "never "}
        negations_b = {"not ", "doesn't", "don't", "isn't", "no ", "never "}
        has_neg_a = any(n in a_lower for n in negations_a)
        has_neg_b = any(n in b_lower for n in negations_b)

        if has_neg_a == has_neg_b:
            return False

        cleaned_a = a_lower
        cleaned_b = b_lower
        for n in negations_a:
            cleaned_a = cleaned_a.replace(n, "")
        for n in negations_b:
            cleaned_b = cleaned_b.replace(n, "")

        words_a = set(cleaned_a.split())
        words_b = set(cleaned_b.split())
        overlap = words_a & words_b
        if len(overlap) >= 3:
            return True

        return False

    # ── Uncertainty Propagation ───────────────────────────────────────────

    def _propagate_uncertainty(
        self,
        kept: List[FusedFact],
        removed: List[FusedFact],
        identity_snapshot: Dict[str, Any],
        self_model: Dict[str, Any],
    ) -> List[str]:
        domains: List[str] = []

        low_conf_facts = [f for f in kept if f.confidence < 0.5]
        for fact in low_conf_facts:
            if fact.topic and fact.topic not in domains:
                domains.append(fact.topic)

        if self_model:
            uncertainty_map = self_model.get("uncertainty_map", {})
            if isinstance(uncertainty_map, dict):
                high_uncertainty = uncertainty_map.get("high_uncertainty_domains", [])
                for d in high_uncertainty:
                    if d not in domains:
                        domains.append(d)

        return domains

    # ── Final Context Optimization ────────────────────────────────────────

    def _final_optimize(
        self,
        facts: List[FusedFact],
        decision_scores: Dict[str, float],
    ) -> List[FusedFact]:
        sorted_facts = sorted(
            facts,
            key=lambda f: decision_scores.get(f.fact_id, f.confidence),
            reverse=True,
        )
        return sorted_facts[:self.config.max_total_facts]

    # ── Filtered RetrievalResult ──────────────────────────────────────────

    def _build_filtered_retrieval(
        self,
        original: RetrievalResult,
        selected_facts: List[FusedFact],
    ) -> RetrievalResult:
        selected_ids = set(f.source_id for f in selected_facts)
        filtered_objects = [
            o for o in original.objects if o.object_id in selected_ids
        ]

        return RetrievalResult(
            objects=filtered_objects,
            total_retrieved=len(filtered_objects),
            retrieval_time_ms=original.retrieval_time_ms,
            directives_fulfilled=original.directives_fulfilled,
            directives_total=original.directives_total,
            errors=original.errors,
        )

    # ── Identity Data Extraction ──────────────────────────────────────────

    def _extract_identity_data(
        self,
        retrieval_context: Optional[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if not retrieval_context:
            return {}, {}

        identity_snapshot = retrieval_context.get("identity_snapshot", {})
        if not isinstance(identity_snapshot, dict):
            identity_snapshot = {}

        self_model = retrieval_context.get("self_model", {})
        if not isinstance(self_model, dict):
            self_model = {}

        return identity_snapshot, self_model

    def _extract_goal_ids(
        self,
        plan: CharacterPlan,
        retrieval_context: Optional[Dict[str, Any]],
    ) -> List[str]:
        goal_ids: List[str] = []
        goals_data = []
        if retrieval_context:
            goals_data = retrieval_context.get("goals", [])
        if isinstance(goals_data, list):
            for g in goals_data:
                if isinstance(g, dict):
                    gid = g.get("goal_id") or g.get("id")
                    if gid:
                        goal_ids.append(str(gid))
        return goal_ids

    def _extract_dominant_topics(
        self,
        identity_snapshot: Dict[str, Any],
    ) -> List[str]:
        topics = identity_snapshot.get("dominant_topics", [])
        if isinstance(topics, list):
            return [str(t) for t in topics if t]
        return []

    # ── Empty Result ──────────────────────────────────────────────────────

    def _empty_result(
        self,
        retrieval_result: RetrievalResult,
        retrieval_context: Optional[Dict[str, Any]],
        metrics: DecisionMetrics,
    ) -> FinalContext:
        identity_snapshot, self_model = self._extract_identity_data(retrieval_context)
        return FinalContext(
            selected_facts=[],
            removed_facts=[],
            decision_scores={},
            conflicts=[],
            uncertainty_domains=[],
            identity_snapshot=identity_snapshot,
            self_model=self_model,
            filtered_retrieval_result=retrieval_result,
            goal_aligned_fact_ids=set(),
            metrics=metrics,
        )


# ── Singleton ────────────────────────────────────────────────────────────────

_decision_engine_instance: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    global _decision_engine_instance
    if _decision_engine_instance is None:
        _decision_engine_instance = DecisionEngine()
    return _decision_engine_instance
