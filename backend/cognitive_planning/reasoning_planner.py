"""
Reasoning Planner — Reasoning Mode Selection

Determines which reasoning pipeline is required for the query.
Architecture V3 — FROZEN. No redesign.
"""
import re
import logging
from typing import List, Optional
from .planner_models import (
    IntentPlan, RetrievalPlan, ReasoningPlan, ReasoningMode,
    UserIntentType
)

logger = logging.getLogger(__name__)

_INTENT_PRIMARY_MODE: dict = {
    UserIntentType.INFORMATION: ReasoningMode.EVIDENCE_AGGREGATION,
    UserIntentType.RECOMMENDATION: ReasoningMode.CONFIDENCE_ESTIMATION,
    UserIntentType.EXPLANATION: ReasoningMode.IDENTITY_EXPLANATION,
    UserIntentType.REFLECTION: ReasoningMode.INTEREST_EVOLUTION,
    UserIntentType.COMPARISON: ReasoningMode.BEHAVIOR_COMPARISON,
    UserIntentType.PREDICTION: ReasoningMode.TEMPORAL_REASONING,
    UserIntentType.COACHING: ReasoningMode.GOAL_REASONING,
    UserIntentType.IDENTITY_QUESTION: ReasoningMode.IDENTITY_EXPLANATION,
    UserIntentType.MEMORY_QUESTION: ReasoningMode.EVIDENCE_AGGREGATION,
    UserIntentType.BEHAVIORAL_QUESTION: ReasoningMode.BEHAVIOR_COMPARISON,
    UserIntentType.UNKNOWN: ReasoningMode.EVIDENCE_AGGREGATION,
}

_INTENT_SECONDARY_MODES: dict = {
    UserIntentType.INFORMATION: [ReasoningMode.CONFIDENCE_ESTIMATION],
    UserIntentType.RECOMMENDATION: [
        ReasoningMode.CONFIDENCE_ESTIMATION, ReasoningMode.GOAL_REASONING],
    UserIntentType.EXPLANATION: [
        ReasoningMode.UNCERTAINTY_REASONING, ReasoningMode.COUNTER_EVIDENCE],
    UserIntentType.REFLECTION: [
        ReasoningMode.TEMPORAL_REASONING, ReasoningMode.CONFIDENCE_ESTIMATION],
    UserIntentType.COMPARISON: [
        ReasoningMode.TREND_EXPLANATION, ReasoningMode.UNCERTAINTY_REASONING],
    UserIntentType.PREDICTION: [
        ReasoningMode.TREND_EXPLANATION, ReasoningMode.UNCERTAINTY_REASONING],
    UserIntentType.COACHING: [
        ReasoningMode.CONFLICT_RESOLUTION, ReasoningMode.CONFIDENCE_ESTIMATION],
    UserIntentType.IDENTITY_QUESTION: [
        ReasoningMode.UNCERTAINTY_REASONING, ReasoningMode.TREND_EXPLANATION],
    UserIntentType.MEMORY_QUESTION: [ReasoningMode.TEMPORAL_REASONING],
    UserIntentType.BEHAVIORAL_QUESTION: [
        ReasoningMode.TEMPORAL_REASONING, ReasoningMode.TREND_EXPLANATION],
    UserIntentType.UNKNOWN: [],
}

_PREDICTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(will|future|next|trend|continue|forecast|predict)\b", re.I),
]
_COUNTER_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(but|however|on the other hand|contrary|disagree|different view)\b", re.I),
]
_UNCERTAINTY_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(not sure|uncertain|maybe|perhaps|might|could|possibly)\b", re.I),
]
_CONFLICT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(conflict|contradict|inconsistent|opposite|confusing)\b", re.I),
]


class ReasoningPlanner:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.default_depth = self.config.get("default_reasoning_depth", 0.5)

    def plan(
        self,
        intent: IntentPlan,
        query: str = ""
    ) -> ReasoningPlan:
        primary = _INTENT_PRIMARY_MODE.get(
            intent.intent_type, ReasoningMode.EVIDENCE_AGGREGATION)
        secondary = list(_INTENT_SECONDARY_MODES.get(intent.intent_type, []))

        query_lower = query.lower()

        if any(p.search(query_lower) for p in _PREDICTION_PATTERNS):
            if ReasoningMode.TEMPORAL_REASONING not in secondary:
                secondary.append(ReasoningMode.TEMPORAL_REASONING)

        if any(p.search(query_lower) for p in _COUNTER_PATTERNS):
            if ReasoningMode.COUNTER_EVIDENCE not in secondary:
                secondary.append(ReasoningMode.COUNTER_EVIDENCE)

        if any(p.search(query_lower) for p in _UNCERTAINTY_PATTERNS):
            if ReasoningMode.UNCERTAINTY_REASONING not in secondary:
                secondary.append(ReasoningMode.UNCERTAINTY_REASONING)

        if any(p.search(query_lower) for p in _CONFLICT_PATTERNS):
            if ReasoningMode.CONFLICT_RESOLUTION not in secondary:
                secondary.append(ReasoningMode.CONFLICT_RESOLUTION)

        depth = self.default_depth
        if intent.requires_comparison or intent.requires_temporal_analysis:
            depth = min(1.0, depth + 0.2)

        return ReasoningPlan(
            primary_mode=primary,
            secondary_modes=secondary[:3],
            reasoning_depth=depth,
            requires_counter_evidence=ReasoningMode.COUNTER_EVIDENCE in secondary,
            requires_temporal_trend=ReasoningMode.TEMPORAL_REASONING in secondary
            or ReasoningMode.TREND_EXPLANATION in secondary,
            requires_goal_alignment=ReasoningMode.GOAL_REASONING in secondary,
            requires_uncertainty_estimation=ReasoningMode.UNCERTAINTY_REASONING in secondary,
            required_evidence_min=1 if intent.intent_confidence < 0.5 else 2,
            confidence_threshold=0.4 if intent.ambiguity_score > 0.3 else 0.5,
        )


def get_reasoning_planner() -> ReasoningPlanner:
    if not hasattr(get_reasoning_planner, "_instance"):
        get_reasoning_planner._instance = ReasoningPlanner()
    return get_reasoning_planner._instance
