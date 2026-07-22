"""
Cognitive Planning Models

All schema definitions for the cognitive planning layer.
Architecture V3 — FROZEN. No redesign.
"""
from __future__ import annotations
import uuid
import logging
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UserIntentType(str, Enum):
    INFORMATION = "information"
    RECOMMENDATION = "recommendation"
    EXPLANATION = "explanation"
    REFLECTION = "reflection"
    COMPARISON = "comparison"
    PREDICTION = "prediction"
    COACHING = "coaching"
    IDENTITY_QUESTION = "identity_question"
    MEMORY_QUESTION = "memory_question"
    BEHAVIORAL_QUESTION = "behavioral_question"
    UNKNOWN = "unknown"


class RetrievalTarget(str, Enum):
    BEHAVIOR_OBJECTS = "behavior_objects"
    EVIDENCE = "evidence"
    IDENTITY_SNAPSHOT = "identity_snapshot"
    SELF_MODEL = "self_model"
    GOALS = "goals"
    REFLECTIONS = "reflections"
    INFERENCES = "inferences"
    BEHAVIOR_HISTORY = "behavior_history"
    CREATOR_HISTORY = "creator_history"
    INTEREST_HISTORY = "interest_history"
    JOURNAL = "journal"
    MEMORY = "memory"
    RUNTIME_STATE = "runtime_state"


class ReasoningMode(str, Enum):
    EVIDENCE_AGGREGATION = "evidence_aggregation"
    BEHAVIOR_COMPARISON = "behavior_comparison"
    IDENTITY_EXPLANATION = "identity_explanation"
    INTEREST_EVOLUTION = "interest_evolution"
    TEMPORAL_REASONING = "temporal_reasoning"
    GOAL_REASONING = "goal_reasoning"
    CONFLICT_RESOLUTION = "conflict_resolution"
    COUNTER_EVIDENCE = "counter_evidence"
    TREND_EXPLANATION = "trend_explanation"
    CONFIDENCE_ESTIMATION = "confidence_estimation"
    UNCERTAINTY_REASONING = "uncertainty_reasoning"


class ResponseStructure(str, Enum):
    TECHNICAL = "technical"
    CONCISE = "concise"
    DEEP_EXPLANATION = "deep_explanation"
    COACHING = "coaching"
    REFLECTIVE = "reflective"
    MOTIVATIONAL = "motivational"
    RESEARCH = "research"


class CommunicationStyleVector(BaseModel):
    verbosity: float = Field(default=0.5, ge=0.0, le=1.0)
    technical_depth: float = Field(default=0.5, ge=0.0, le=1.0)
    detail: float = Field(default=0.5, ge=0.0, le=1.0)
    examples: float = Field(default=0.5, ge=0.0, le=1.0)
    curiosity: float = Field(default=0.5, ge=0.0, le=1.0)
    precision: float = Field(default=0.5, ge=0.0, le=1.0)
    formality: float = Field(default=0.5, ge=0.0, le=1.0)
    reflection: float = Field(default=0.5, ge=0.0, le=1.0)
    motivation: float = Field(default=0.5, ge=0.0, le=1.0)
    humor: float = Field(default=0.0, ge=0.0, le=1.0)


class IntentPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"intent_{uuid.uuid4().hex[:8]}")
    intent_type: UserIntentType
    intent_confidence: float = Field(..., ge=0.0, le=1.0)
    primary_question: str = ""
    key_entities: List[str] = Field(default_factory=list)
    key_topics: List[str] = Field(default_factory=list)
    time_reference: Optional[str] = None
    requires_comparison: bool = False
    requires_temporal_analysis: bool = False
    requires_identity_access: bool = False
    requires_memory_access: bool = False
    requires_behavioral_data: bool = False
    requires_goal_data: bool = False
    requires_prediction: bool = False
    alternatives: List[UserIntentType] = Field(default_factory=list)
    ambiguity_score: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievalDirective(BaseModel):
    target: RetrievalTarget
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=100)
    required: bool = False
    filter_topics: List[str] = Field(default_factory=list)
    filter_timerange_days: Optional[int] = None
    filter_confidence_min: Optional[float] = None


class RetrievalPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"retrieval_{uuid.uuid4().hex[:8]}")
    directives: List[RetrievalDirective] = Field(default_factory=list)
    total_max_results: int = Field(default=50, ge=1)
    prioritize_recency: bool = True
    prioritize_confidence: bool = True
    deduplicate: bool = True
    estimated_cost: float = Field(default=0.0, ge=0.0)


class ReasoningPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"reason_{uuid.uuid4().hex[:8]}")
    primary_mode: ReasoningMode
    secondary_modes: List[ReasoningMode] = Field(default_factory=list)
    reasoning_depth: float = Field(default=0.5, ge=0.0, le=1.0)
    requires_counter_evidence: bool = False
    requires_temporal_trend: bool = False
    requires_goal_alignment: bool = False
    requires_uncertainty_estimation: bool = False
    required_evidence_min: int = Field(default=1, ge=0)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class ResponsePlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"response_{uuid.uuid4().hex[:8]}")
    primary_structure: ResponseStructure
    secondary_structure: Optional[ResponseStructure] = None
    style_vector: CommunicationStyleVector = Field(default_factory=CommunicationStyleVector)
    max_sections: int = Field(default=5, ge=1, le=20)
    include_citations: bool = True
    include_evidence_summary: bool = True
    include_uncertainty: bool = True
    section_order: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)


class CharacterPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"charplan_{uuid.uuid4().hex[:8]}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = ""
    intent_plan: IntentPlan
    retrieval_plan: RetrievalPlan
    reasoning_plan: ReasoningPlan
    response_plan: ResponsePlan
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_flags: List[str] = Field(default_factory=list)
    uncertainty_domains: List[str] = Field(default_factory=list)
    required_memories: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_summary(self) -> str:
        return (
            f"Plan {self.plan_id}: intent={self.intent_plan.intent_type.value}, "
            f"reasoning={self.reasoning_plan.primary_mode.value}, "
            f"response={self.response_plan.primary_structure.value}, "
            f"confidence={self.overall_confidence:.2f}"
        )
