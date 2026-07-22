"""
Planner Orchestrator — CharacterPlan Builder

Combines Intent, Retrieval, Reasoning, and Response plans into a CharacterPlan.
Architecture V3 — FROZEN. No redesign.
"""
import time
import logging
from typing import Optional, List
from .planner_models import (
    CharacterPlan, IntentPlan, RetrievalPlan, ReasoningPlan, ResponsePlan,
    UserIntentType
)
from .intent_planner import IntentPlanner, get_intent_planner
from .retrieval_planner import RetrievalPlanner, get_retrieval_planner
from .reasoning_planner import ReasoningPlanner, get_reasoning_planner
from .response_planner import ResponsePlanner, get_response_planner
from .planner_metrics import PlannerMetrics, get_planner_metrics

logger = logging.getLogger(__name__)


class PlannerOrchestrator:
    def __init__(
        self,
        intent_planner: Optional[IntentPlanner] = None,
        retrieval_planner: Optional[RetrievalPlanner] = None,
        reasoning_planner: Optional[ReasoningPlanner] = None,
        response_planner: Optional[ResponsePlanner] = None,
        metrics: Optional[PlannerMetrics] = None,
        config: Optional[dict] = None,
    ):
        self.intent_planner = intent_planner or get_intent_planner()
        self.retrieval_planner = retrieval_planner or get_retrieval_planner()
        self.reasoning_planner = reasoning_planner or get_reasoning_planner()
        self.response_planner = response_planner or get_response_planner()
        self.metrics = metrics or get_planner_metrics()
        self.config = config or {}
        self.min_plan_confidence = self.config.get("min_plan_confidence", 0.1)

    def build_plan(
        self,
        user_id: str,
        query: str,
        override_intent: Optional[IntentPlan] = None,
    ) -> CharacterPlan:
        start = time.perf_counter()

        t0 = time.perf_counter()
        intent = override_intent or self.intent_planner.classify(query)
        t1 = time.perf_counter()
        self.metrics.record_intent_time((t1 - t0) * 1000)
        self.metrics.record_intent_type(intent.intent_type.value)

        retrieval = self.retrieval_planner.plan(intent)
        t2 = time.perf_counter()
        self.metrics.record_retrieval_time((t2 - t1) * 1000)

        reasoning = self.reasoning_planner.plan(intent, query)
        t3 = time.perf_counter()
        self.metrics.record_reasoning_time((t3 - t2) * 1000)
        self.metrics.record_reasoning_mode(reasoning.primary_mode.value)

        style = self.intent_planner.compute_style_vector(intent)
        response = self.response_planner.plan(intent, reasoning, style)
        t4 = time.perf_counter()
        self.metrics.record_response_time((t4 - t3) * 1000)
        self.metrics.record_response_structure(response.primary_structure.value)

        overall_confidence = intent.intent_confidence * 0.4 + reasoning.confidence_threshold * 0.3 + 0.3
        risk_flags = self._compute_risk_flags(intent, reasoning)
        uncertainty_domains = (
            reasoning.secondary_modes
            if reasoning.requires_uncertainty_estimation
            else []
        )

        plan = CharacterPlan(
            user_id=user_id,
            intent_plan=intent,
            retrieval_plan=retrieval,
            reasoning_plan=reasoning,
            response_plan=response,
            overall_confidence=overall_confidence,
            risk_flags=risk_flags,
            uncertainty_domains=[m.value for m in uncertainty_domains],
            required_memories=[
                d.target.value for d in retrieval.directives if d.required
            ],
        )

        elapsed = (time.perf_counter() - start) * 1000
        self.metrics.record_orchestration_time(elapsed)
        self.metrics.record_plan()
        self.metrics.record_confidence(plan.overall_confidence)

        logger.info(
            f"CharacterPlan built: {intent.intent_type.value} | "
            f"{reasoning.primary_mode.value} | {response.primary_structure.value} | "
            f"confidence={plan.overall_confidence:.2f} | {elapsed:.1f}ms"
        )
        return plan

    def _compute_risk_flags(self, intent: IntentPlan, reasoning: ReasoningPlan) -> List[str]:
        flags = []
        if intent.ambiguity_score > 0.5:
            flags.append("high_ambiguity")
        if intent.intent_confidence < 0.3:
            flags.append("low_intent_confidence")
        if reasoning.requires_uncertainty_estimation:
            flags.append("high_uncertainty_expected")
        if reasoning.requires_counter_evidence:
            flags.append("counter_evidence_required")
        if reasoning.required_evidence_min > 5:
            flags.append("high_evidence_requirement")
        return flags


_orchestrator_instance: Optional[PlannerOrchestrator] = None


def get_planner_orchestrator() -> PlannerOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = PlannerOrchestrator()
    return _orchestrator_instance
