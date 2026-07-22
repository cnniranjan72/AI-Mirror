"""
Cognitive Pipeline Trace — Explainability & Debugging

Records every stage of pipeline execution with timing, IDs, confidence.
Architecture V3 — FROZEN. No redesign.
"""
import time
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import datetime


@dataclass
class PipelineTrace:
    user_id: str
    query: str
    started_at: datetime = field(default_factory=datetime.utcnow)

    runtime_load_ms: float = 0.0
    snapshot_id: Optional[str] = None
    snapshot_version: Optional[int] = None
    self_model_id: Optional[str] = None
    inference_count: int = 0
    goal_count: int = 0
    reflection_count: int = 0
    behavior_object_count: int = 0
    evidence_count: int = 0

    planning_ms: float = 0.0
    intent_type: Optional[str] = None
    intent_confidence: Optional[float] = None
    reasoning_mode: Optional[str] = None
    response_structure: Optional[str] = None
    plan_confidence: Optional[float] = None
    risk_flags: List[str] = field(default_factory=list)
    retrieval_directives: List[str] = field(default_factory=list)

    retrieval_ms: float = 0.0
    retrieved_count: int = 0
    directives_fulfilled: int = 0
    directives_total: int = 0
    retrieval_errors: List[str] = field(default_factory=list)

    ranking_ms: float = 0.0

    fusion_ms: float = 0.0
    facts_generated: int = 0
    citations_created: int = 0
    duplicates_removed: int = 0
    aggregate_confidence: Optional[float] = None

    decision_ms: float = 0.0
    decision_input_facts: int = 0
    decision_output_facts: int = 0
    decision_conflicts: int = 0
    decision_removed_low_confidence: int = 0
    decision_removed_duplicates: int = 0
    decision_removed_diversity: int = 0

    context_build_ms: float = 0.0
    context_id: Optional[str] = None

    verbalization_ms: float = 0.0
    token_count: int = 0
    response_length: int = 0

    total_ms: float = 0.0
    success: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: str(v) if isinstance(v, datetime) else v for k, v in self.__dict__.items()}

    def summary(self) -> str:
        return (
            f"Trace[{self.user_id}] query='{self.query[:60]}' "
            f"intent={self.intent_type or '?'} plan_conf={f'{self.plan_confidence:.2f}' if self.plan_confidence is not None else 'N/A'} "
            f"retrieved={self.retrieved_count} facts={self.facts_generated if self.facts_generated else 0} "
            f"citations={self.citations_created} tokens={self.token_count} "
            f"decision={self.decision_input_facts}->{self.decision_output_facts} "
            f"total={self.total_ms:.1f}ms"
        )
