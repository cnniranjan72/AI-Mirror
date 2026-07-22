"""
Fusion Engine — Multi-Source Evidence Fusion

Merges Identity, Evidence, Memory, Reflection, Inference, Goals, Behavior
into one coherent reasoning context.
Never duplicates information. Preserves provenance.
Architecture V3 — FROZEN. No redesign.
"""
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
from pydantic import BaseModel, Field

from .retriever import RetrievedObject, RetrievalResult
from .citation_manager import Citation, CitationManager, get_citation_manager
from .memory_ranker import RankedObject

logger = logging.getLogger(__name__)


class FusedFact(BaseModel):
    fact_id: str = Field(..., description="Unique fact identifier")
    claim: str = Field(..., description="The factual statement")
    source_type: str = Field(..., description="Provenance source type")
    source_id: str = Field(..., description="Provenance source ID")
    confidence: float = Field(..., ge=0.0, le=1.0)
    citation_id: str = Field(..., description="Link to citation")
    timestamp: Optional[datetime] = None
    topic: Optional[str] = None
    supporting_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FusedEvidence(BaseModel):
    facts: List[FusedFact] = Field(default_factory=list)
    fusion_time_ms: float = 0.0
    total_sources_merged: int = 0
    facts_generated: int = 0
    duplicates_removed: int = 0
    citations_created: int = 0
    aggregate_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    def has_sufficient_evidence(self, min_facts: int = 2) -> bool:
        return len(self.facts) >= min_facts

    def get_facts_by_topic(self, topic: str) -> List[FusedFact]:
        return [f for f in self.facts if f.topic and topic.lower() in f.topic.lower()]

    def get_facts_by_source(self, source_type: str) -> List[FusedFact]:
        return [f for f in self.facts if f.source_type == source_type]

    def get_high_confidence_facts(self, threshold: float = 0.7) -> List[FusedFact]:
        return [f for f in self.facts if f.confidence >= threshold]


PROVENANCE_CLAIM_TEMPLATES: Dict[str, str] = {
    "behavior_object": "User engaged with {topic} content (confidence: {confidence:.2f})",
    "evidence": "Evidence indicates {summary}",
    "identity_snapshot": "Identity snapshot shows {topic_count} dominant topics, confidence {confidence:.2f}",
    "self_model": "Self model contains {belief_count} beliefs, {strong} strong",
    "goal": "User has active goal: {description}",
    "reflection": "Reflection highlights: {insights}",
    "inference": "Inferred {label}: {description}",
    "memory": "Memory reference: {summary}",
}


class FusionEngine:
    def __init__(
        self,
        citation_manager: Optional[CitationManager] = None,
        config: Optional[dict] = None,
    ):
        self.citation_manager = citation_manager or get_citation_manager()
        self.config = config or {}

    def fuse(
        self,
        retrieval_result: RetrievalResult,
        ranked_objects: Optional[List[RankedObject]] = None,
    ) -> FusedEvidence:
        start = time.perf_counter()
        facts: List[FusedFact] = []
        seen_claims: Set[str] = set()
        duplicates = 0

        source_order = self.config.get("source_priority", [
            "identity_snapshot", "self_model", "inference",
            "evidence", "behavior_object", "goal",
            "reflection", "memory",
        ])
        sources: Dict[str, List[RetrievedObject]] = {}
        for obj in retrieval_result.objects:
            st = obj.source_type
            if st not in sources:
                sources[st] = []
            sources[st].append(obj)

        for source_type in source_order:
            objects = sources.get(source_type, [])
            if ranked_objects:
                rank_map = {r.retrieved.object_id: r for r in ranked_objects}
                objects.sort(key=lambda o: rank_map.get(o.object_id, RankedObject(retrieved=o, rank_score=0.0)).rank_score, reverse=True)

            for obj in objects:
                fact = self._object_to_fact(obj)
                if fact is None:
                    continue
                claim_key = fact.claim.lower().strip()
                if claim_key in seen_claims:
                    duplicates += 1
                    continue
                seen_claims.add(claim_key)
                citation = self.citation_manager.create_citation(
                    source_type=fact.source_type,
                    source_id=fact.source_id,
                    content_summary=fact.claim[:120],
                    confidence=fact.confidence,
                    timestamp=fact.timestamp,
                    supporting_evidence_ids=obj.content.get("evidence_references", []) if isinstance(obj.content, dict) else [],
                    supporting_behavior_ids=obj.content.get("supporting_behavior_objects", []) if isinstance(obj.content, dict) else [],
                )
                fact.citation_id = citation.citation_id
                facts.append(fact)

        elapsed = (time.perf_counter() - start) * 1000
        aggregate_conf = sum(f.confidence for f in facts) / len(facts) if facts else 0.0

        return FusedEvidence(
            facts=facts,
            fusion_time_ms=elapsed,
            total_sources_merged=len(sources),
            facts_generated=len(facts),
            duplicates_removed=duplicates,
            citations_created=len(self.citation_manager.all_citations()),
            aggregate_confidence=aggregate_conf,
        )

    def _object_to_fact(self, obj: RetrievedObject) -> Optional[FusedFact]:
        content = obj.content if isinstance(obj.content, dict) else {}
        template = PROVENANCE_CLAIM_TEMPLATES.get(obj.source_type)
        if template:
            try:
                claim = template.format(
                    topic=content.get("topic", "unknown"),
                    confidence=obj.confidence,
                    summary=content.get("explanation", content.get("summary", "unknown")),
                    topic_count=len(content.get("dominant_topics", content.get("topics", []))),
                    belief_count=len(content.get("beliefs", [])),
                    strong=len(content.get("strong_beliefs", [])),
                    description=content.get("description", content.get("goal_description", "")),
                    insights=", ".join(content.get("key_insights", [])[:3]),
                    label=content.get("label", "unknown"),
                )
            except (KeyError, ValueError):
                claim = f"{obj.source_type}: {obj.object_id}"
        else:
            topic_str = f" ({obj.topic})" if obj.topic else ""
            claim = f"{obj.source_type}{topic_str}: {obj.object_id}"

        supporting_ids: List[str] = []
        if isinstance(content, dict):
            for key in ("evidence_references", "supporting_evidence_ids",
                        "source_evidence", "supporting_behavior_objects",
                        "source_behavior_objects"):
                val = content.get(key, [])
                if isinstance(val, list):
                    supporting_ids.extend(val)

        return FusedFact(
            fact_id=f"fact_{obj.source_type}_{obj.object_id[:16]}_fusion",
            claim=claim,
            source_type=obj.source_type,
            source_id=obj.object_id,
            confidence=obj.confidence,
            citation_id="",
            timestamp=obj.timestamp,
            topic=obj.topic or content.get("topic") if isinstance(content, dict) else None,
            supporting_ids=supporting_ids[:10],
        )


_fusion_engine_instance: Optional[FusionEngine] = None


def get_fusion_engine() -> FusionEngine:
    global _fusion_engine_instance
    if _fusion_engine_instance is None:
        _fusion_engine_instance = FusionEngine()
    return _fusion_engine_instance
