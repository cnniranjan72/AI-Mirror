"""
Cognitive Intelligence Layer for AIMirror
Reasoning, Evidence, and Behavioral Inference
"""

from .behavior_object import (
    BehaviorObject,
    EvolutionSnapshot,
    BehaviorLifecycleState,
    TrendDirection,
    EngagementStatistics,
    WatchStatistics,
    TemporalStatistics,
    TrendInformation
)
from .evidence_engine import Evidence, EvidenceType, EvidenceEngine, get_evidence_engine
from .reasoning_context import (
    ReasoningContext,
    TemporalContext,
    MemoryReference,
    GoalReference,
    ReflectionReference
)
from .inference_engine import Inference, InferenceEngine, get_inference_engine
from .reflection_engine import ReflectionEngine, Reflection, get_reflection_engine
from .rules import Rule, RuleEngine, get_rule_engine

__all__ = [
    # Behavior Object
    "BehaviorObject",
    "EvolutionSnapshot",
    "BehaviorLifecycleState",
    "TrendDirection",
    "EngagementStatistics",
    "WatchStatistics",
    "TemporalStatistics",
    "TrendInformation",
    # Evidence
    "Evidence",
    "EvidenceType",
    "EvidenceEngine",
    "get_evidence_engine",
    # Reasoning Context
    "ReasoningContext",
    "TemporalContext",
    "MemoryReference",
    "GoalReference",
    "ReflectionReference",
    # Inference
    "Inference",
    "InferenceEngine",
    "get_inference_engine",
    # Reflection
    "Reflection",
    "ReflectionEngine",
    "get_reflection_engine",
    # Rules
    "Rule",
    "RuleEngine",
    "get_rule_engine"
]
