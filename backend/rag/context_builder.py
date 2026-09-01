"""
Context Builder — CharacterContext Construction

Constructs CharacterContext containing Identity Snapshot, Self Model,
Behavior Objects, Evidence, Goals, Reflections, Inferences, Memory References,
Character Plan. Everything fully structured.
Architecture V3 — FROZEN. No redesign.
"""
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.cognitive_planning.planner_models import CommunicationStyleVector
from .retriever import RetrievalResult, RetrievedObject
from .fusion import FusedEvidence, FusedFact

logger = logging.getLogger(__name__)


class CharacterContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    context_id: str = Field(default_factory=lambda: f"ctx_{int(time.time() * 1000000)}")
    built_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = ""

    identity_snapshot: Dict[str, Any] = Field(default_factory=dict)
    self_model: Dict[str, Any] = Field(default_factory=dict)
    behavior_objects: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    goals: List[Dict[str, Any]] = Field(default_factory=list)
    reflections: List[Dict[str, Any]] = Field(default_factory=list)
    inferences: List[Dict[str, Any]] = Field(default_factory=list)
    memory_references: List[Dict[str, Any]] = Field(default_factory=list)

    character_plan: Optional[Any] = None

    fused_evidence: Optional[FusedEvidence] = None
    dominant_topics: List[str] = Field(default_factory=list)
    emerging_topics: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty_domains: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)

    # Findings from the two audits, pre-computed by their own deterministic
    # scorers and carried here as FACTS. The verbalizer may phrase them; it may
    # never derive them. "You were fed this interest" is a conclusion with a
    # measurement behind it, and letting a language model reach it on vibes
    # would break the one guarantee this product makes.
    # Each dict also carries its own reliability flag, so a thin account cannot
    # have a verdict spoken about it in chat that the Report would withhold.
    platform_audit: Dict[str, Any] = Field(default_factory=dict)
    interest_provenance: Dict[str, Any] = Field(default_factory=dict)

    build_time_ms: float = 0.0
    citation_count: int = 0

    def get_summary(self) -> str:
        return (
            f"CharacterContext: {len(self.behavior_objects)} behaviors, "
            f"{len(self.evidence)} evidence, {len(self.inferences)} inferences, "
            f"confidence={self.overall_confidence:.2f}, "
            f"topics={self.dominant_topics[:3]}"
        )

    def has_reasoning_context(self) -> bool:
        return self.character_plan is not None

    def get_confidence_level(self) -> str:
        if self.overall_confidence >= 0.7:
            return "high"
        if self.overall_confidence >= 0.4:
            return "medium"
        return "low"


class ContextBuilder:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.max_behavior_objects = self.config.get("max_behavior_objects", 20)
        self.max_evidence = self.config.get("max_evidence", 20)
        self.max_inferences = self.config.get("max_inferences", 15)
        self.max_goals = self.config.get("max_goals", 10)
        self.max_reflections = self.config.get("max_reflections", 10)

    def build(
        self,
        user_id: str,
        retrieval_result: RetrievalResult,
        character_plan: Any,
        fused_evidence: Optional[FusedEvidence] = None,
        identity_snapshot: Optional[Dict[str, Any]] = None,
        self_model: Optional[Dict[str, Any]] = None,
        platform_audit: Optional[Dict[str, Any]] = None,
        interest_provenance: Optional[Dict[str, Any]] = None,
    ) -> CharacterContext:
        start = time.perf_counter()

        categorized: Dict[str, List[Dict[str, Any]]] = {
            "behavior_objects": [],
            "evidence": [],
            "goals": [],
            "reflections": [],
            "inferences": [],
            "memory_references": [],
        }

        source_type_key_map = {
            "behavior_object": "behavior_objects",
            "behavior_objects": "behavior_objects",
            "evidence": "evidence",
            "goal": "goals",
            "goals": "goals",
            "reflection": "reflections",
            "reflections": "reflections",
            "inference": "inferences",
            "inferences": "inferences",
            "memory_reference": "memory_references",
            "memory_references": "memory_references",
        }

        identity_snapshot_data: Dict[str, Any] = identity_snapshot or {}
        self_model_data: Dict[str, Any] = self_model or {}

        for obj in retrieval_result.objects:
            content = obj.content
            st = obj.source_type
            if st == "identity_snapshot":
                identity_snapshot_data = content if isinstance(content, dict) else {}
            elif st == "self_model":
                self_model_data = content if isinstance(content, dict) else {}
            else:
                key = source_type_key_map.get(st)
                if key and isinstance(content, dict):
                    categorized[key].append(content)

        dominant_topics = identity_snapshot_data.get("dominant_topics", [])
        if isinstance(dominant_topics, list):
            dominant_topics = [str(t) for t in dominant_topics]

        emerging_topics = identity_snapshot_data.get("emerging_topics", [])
        if isinstance(emerging_topics, list):
            emerging_topics = [str(t) for t in emerging_topics]

        overall_confidence = (
            fused_evidence.aggregate_confidence
            if fused_evidence
            else identity_snapshot_data.get("overall_confidence", 0.0)
        )

        uncertainty_domains = []
        if self_model_data:
            uncertainty_map = self_model_data.get("uncertainty_map", {})
            if isinstance(uncertainty_map, dict):
                uncertainty_domains = uncertainty_map.get("high_uncertainty_domains", [])

        ctx = CharacterContext(
            user_id=user_id,
            identity_snapshot=identity_snapshot_data,
            self_model=self_model_data,
            behavior_objects=categorized["behavior_objects"][:self.max_behavior_objects],
            evidence=categorized["evidence"][:self.max_evidence],
            goals=categorized["goals"][:self.max_goals],
            reflections=categorized["reflections"][:self.max_reflections],
            inferences=categorized["inferences"][:self.max_inferences],
            memory_references=categorized["memory_references"][:self.max_behavior_objects],
            character_plan=character_plan,
            fused_evidence=fused_evidence,
            dominant_topics=dominant_topics,
            emerging_topics=emerging_topics,
            overall_confidence=float(overall_confidence) if overall_confidence else 0.0,
            uncertainty_domains=uncertainty_domains,
            risk_flags=character_plan.risk_flags,
            platform_audit=platform_audit or {},
            interest_provenance=interest_provenance or {},
        )

        elapsed = (time.perf_counter() - start) * 1000
        ctx.build_time_ms = elapsed
        if fused_evidence:
            ctx.citation_count = fused_evidence.citations_created

        logger.info(
            f"CharacterContext built: {len(ctx.behavior_objects)} behaviors, "
            f"{len(ctx.evidence)} evidence, {len(ctx.inferences)} inferences | "
            f"{elapsed:.1f}ms"
        )
        return ctx


_context_builder_instance: Optional[ContextBuilder] = None


def get_context_builder() -> ContextBuilder:
    global _context_builder_instance
    if _context_builder_instance is None:
        _context_builder_instance = ContextBuilder()
    return _context_builder_instance
