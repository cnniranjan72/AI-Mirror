"""
Response Planner — Response Structure Planner

Determines response structure without generating text.
Architecture V3 — FROZEN. No redesign.
"""
import logging
from typing import List, Optional
from .planner_models import (
    IntentPlan, ReasoningPlan, ResponsePlan, ResponseStructure,
    CommunicationStyleVector, UserIntentType, ReasoningMode
)

logger = logging.getLogger(__name__)

_INTENT_STRUCTURE: dict = {
    UserIntentType.INFORMATION: ResponseStructure.TECHNICAL,
    UserIntentType.RECOMMENDATION: ResponseStructure.CONCISE,
    UserIntentType.EXPLANATION: ResponseStructure.DEEP_EXPLANATION,
    UserIntentType.REFLECTION: ResponseStructure.REFLECTIVE,
    UserIntentType.COMPARISON: ResponseStructure.RESEARCH,
    UserIntentType.PREDICTION: ResponseStructure.RESEARCH,
    UserIntentType.COACHING: ResponseStructure.COACHING,
    UserIntentType.IDENTITY_QUESTION: ResponseStructure.REFLECTIVE,
    UserIntentType.MEMORY_QUESTION: ResponseStructure.CONCISE,
    UserIntentType.BEHAVIORAL_QUESTION: ResponseStructure.TECHNICAL,
    UserIntentType.UNKNOWN: ResponseStructure.CONCISE,
}

_INTENT_SECONDARY_STRUCTURE: dict = {
    UserIntentType.INFORMATION: ResponseStructure.CONCISE,
    UserIntentType.EXPLANATION: ResponseStructure.TECHNICAL,
    UserIntentType.COMPARISON: ResponseStructure.CONCISE,
}

_SECTION_ORDER_MAP: dict = {
    ResponseStructure.TECHNICAL: [
        "overview", "key_findings", "evidence", "analysis", "conclusion"],
    ResponseStructure.CONCISE: [
        "answer", "key_points"],
    ResponseStructure.DEEP_EXPLANATION: [
        "overview", "background", "evidence", "analysis",
        "implications", "limitations", "conclusion"],
    ResponseStructure.COACHING: [
        "acknowledgment", "assessment", "recommendations",
        "actionable_steps", "encouragement"],
    ResponseStructure.REFLECTIVE: [
        "observation", "patterns", "meaning", "implications", "closing"],
    ResponseStructure.MOTIVATIONAL: [
        "acknowledgment", "strengths", "opportunities", "encouragement", "next_steps"],
    ResponseStructure.RESEARCH: [
        "question", "methodology", "findings", "analysis",
        "comparison", "conclusion"],
}

_KEY_POINTS_MAP: dict = {
    ResponseStructure.TECHNICAL: ["data_summary", "confidence_levels", "key_metrics"],
    ResponseStructure.CONCISE: ["direct_answer", "confidence"],
    ResponseStructure.DEEP_EXPLANATION: [
        "root_cause", "evidence_chain", "uncertainty", "implications"],
    ResponseStructure.COACHING: [
        "current_state", "goal_progress", "action_items"],
    ResponseStructure.REFLECTIVE: [
        "pattern_summary", "change_detection", "growth_areas"],
    ResponseStructure.RESEARCH: [
        "comparison_points", "evidence_strength", "conclusion"],
}


class ResponsePlanner:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

    def plan(
        self,
        intent: IntentPlan,
        reasoning: ReasoningPlan,
        style_override: Optional[CommunicationStyleVector] = None
    ) -> ResponsePlan:
        primary = _INTENT_STRUCTURE.get(
            intent.intent_type, ResponseStructure.CONCISE)
        secondary = _INTENT_SECONDARY_STRUCTURE.get(intent.intent_type)

        style = style_override or intent.compute_style_vector()

        if reasoning.requires_uncertainty_estimation:
            style.precision = max(0.6, style.precision)
            style.technical_depth = max(0.5, style.technical_depth)

        if reasoning.primary_mode == ReasoningMode.COUNTER_EVIDENCE:
            style.precision = max(0.7, style.precision)
            style.detail = max(0.6, style.detail)

        section_order = _SECTION_ORDER_MAP.get(primary, ["answer"])
        key_points = _KEY_POINTS_MAP.get(primary, [])

        max_sections = len(section_order)
        if intent.requires_temporal_analysis:
            max_sections = min(8, max_sections + 2)

        return ResponsePlan(
            primary_structure=primary,
            secondary_structure=secondary,
            style_vector=style,
            max_sections=max_sections,
            include_citations=True,
            include_evidence_summary=True,
            include_uncertainty=reasoning.requires_uncertainty_estimation,
            section_order=section_order,
            key_points=key_points,
        )


def get_response_planner() -> ResponsePlanner:
    if not hasattr(get_response_planner, "_instance"):
        get_response_planner._instance = ResponsePlanner()
    return get_response_planner._instance
