"""
Retrieval Planner — Minimal Retrieval Cost Planning

Determines what information must be retrieved and minimizes retrieval cost.
Architecture V3 — FROZEN. No redesign.
"""
import logging
from typing import List, Optional, Set
from .planner_models import (
    IntentPlan, RetrievalPlan, RetrievalDirective, RetrievalTarget,
    ReasoningPlan
)

logger = logging.getLogger(__name__)

_RETRIEVAL_COST: dict = {
    RetrievalTarget.BEHAVIOR_OBJECTS: 3.0,
    RetrievalTarget.EVIDENCE: 4.0,
    RetrievalTarget.IDENTITY_SNAPSHOT: 1.0,
    RetrievalTarget.SELF_MODEL: 1.0,
    RetrievalTarget.GOALS: 2.0,
    RetrievalTarget.REFLECTIONS: 2.0,
    RetrievalTarget.INFERENCES: 3.0,
    RetrievalTarget.BEHAVIOR_HISTORY: 5.0,
    RetrievalTarget.CREATOR_HISTORY: 4.0,
    RetrievalTarget.INTEREST_HISTORY: 4.0,
    RetrievalTarget.JOURNAL: 3.0,
    RetrievalTarget.MEMORY: 5.0,
    RetrievalTarget.RUNTIME_STATE: 0.5,
}

_INTENT_TO_TARGETS: dict = {
    "information": [
        (RetrievalTarget.RUNTIME_STATE, 0.3, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.5, 1, False),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.6, 10, False),
        (RetrievalTarget.EVIDENCE, 0.4, 10, False),
    ],
    "recommendation": [
        (RetrievalTarget.RUNTIME_STATE, 0.2, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.6, 1, True),
        (RetrievalTarget.SELF_MODEL, 0.5, 1, False),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.7, 15, True),
        (RetrievalTarget.GOALS, 0.5, 5, False),
    ],
    "explanation": [
        (RetrievalTarget.RUNTIME_STATE, 0.2, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.6, 1, True),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.5, 10, False),
        (RetrievalTarget.EVIDENCE, 0.6, 10, True),
        (RetrievalTarget.INFERENCES, 0.5, 10, False),
    ],
    "reflection": [
        (RetrievalTarget.RUNTIME_STATE, 0.3, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.7, 1, True),
        (RetrievalTarget.REFLECTIONS, 0.8, 10, True),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.4, 10, False),
        (RetrievalTarget.INFERENCES, 0.5, 10, False),
    ],
    "comparison": [
        (RetrievalTarget.RUNTIME_STATE, 0.3, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.5, 1, True),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.7, 15, True),
        (RetrievalTarget.EVIDENCE, 0.5, 10, False),
        (RetrievalTarget.BEHAVIOR_HISTORY, 0.6, 10, False),
    ],
    "prediction": [
        (RetrievalTarget.RUNTIME_STATE, 0.3, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.5, 1, True),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.7, 15, True),
        (RetrievalTarget.INFERENCES, 0.6, 10, True),
        (RetrievalTarget.BEHAVIOR_HISTORY, 0.6, 10, False),
        (RetrievalTarget.TREND_HISTORY, 0.5, 10, False) if hasattr(RetrievalTarget, "TREND_HISTORY") else None,
    ],
    "coaching": [
        (RetrievalTarget.RUNTIME_STATE, 0.3, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.6, 1, True),
        (RetrievalTarget.SELF_MODEL, 0.7, 1, True),
        (RetrievalTarget.GOALS, 0.8, 10, True),
        (RetrievalTarget.REFLECTIONS, 0.5, 5, False),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.4, 10, False),
    ],
    "identity_question": [
        (RetrievalTarget.RUNTIME_STATE, 0.2, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.9, 1, True),
        (RetrievalTarget.SELF_MODEL, 0.8, 1, True),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.5, 10, False),
        (RetrievalTarget.INFERENCES, 0.4, 10, False),
        (RetrievalTarget.CREATOR_HISTORY, 0.3, 5, False),
    ],
    "memory_question": [
        (RetrievalTarget.RUNTIME_STATE, 0.2, 5, False),
        (RetrievalTarget.MEMORY, 0.8, 15, True),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.5, 10, False),
        (RetrievalTarget.EVIDENCE, 0.4, 5, False),
    ],
    "behavioral_question": [
        (RetrievalTarget.RUNTIME_STATE, 0.3, 5, False),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.8, 20, True),
        (RetrievalTarget.BEHAVIOR_HISTORY, 0.7, 15, True),
        (RetrievalTarget.EVIDENCE, 0.5, 10, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.4, 1, False),
    ],
    "unknown": [
        (RetrievalTarget.RUNTIME_STATE, 0.5, 5, False),
        (RetrievalTarget.IDENTITY_SNAPSHOT, 0.5, 1, False),
        (RetrievalTarget.BEHAVIOR_OBJECTS, 0.3, 5, False),
    ],
}


class RetrievalPlanner:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.max_total_cost = self.config.get("max_total_cost", 30.0)
        self.default_max_results = self.config.get("default_max_results", 50)

    def plan(
        self,
        intent: IntentPlan,
        reasoning: Optional[ReasoningPlan] = None
    ) -> RetrievalPlan:
        intent_key = intent.intent_type.value
        target_specs = _INTENT_TO_TARGETS.get(intent_key, _INTENT_TO_TARGETS["unknown"])

        directives: List[RetrievalDirective] = []
        total_cost = 0.0

        for spec in target_specs:
            if spec is None:
                continue
            target, priority, max_results, required = spec
            cost = _RETRIEVAL_COST.get(target, 2.0)
            if total_cost + cost > self.max_total_cost:
                logger.debug(f"Skipping {target.value}: would exceed max cost {self.max_total_cost}")
                continue

            directive = RetrievalDirective(
                target=target,
                priority=priority,
                max_results=max_results,
                required=required,
            )

            if intent.key_topics:
                directive.filter_topics = intent.key_topics
            if intent.time_reference:
                directive.filter_timerange_days = 7

            directives.append(directive)
            total_cost += cost

        if reasoning and reasoning.requires_counter_evidence:
            directives.append(RetrievalDirective(
                target=RetrievalTarget.EVIDENCE,
                priority=0.7,
                max_results=10,
                required=False,
            ))

        directives.sort(key=lambda d: d.priority, reverse=True)

        return RetrievalPlan(
            directives=directives,
            total_max_results=self.default_max_results,
            prioritize_recency=True,
            prioritize_confidence=True,
            deduplicate=True,
            estimated_cost=total_cost,
        )


def get_retrieval_planner() -> RetrievalPlanner:
    if not hasattr(get_retrieval_planner, "_instance"):
        get_retrieval_planner._instance = RetrievalPlanner()
    return get_retrieval_planner._instance
