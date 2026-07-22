"""
LLM Verbalizer — Natural Language Only

LLM receives ONLY CharacterContext + CharacterPlan + CommunicationStyleVector.
LLM responsibilities: natural language, formatting, tone, grammar, readability.
LLM NEVER: reasons, infers, decides, plans, retrieves memory, constructs identity.
Architecture V3 — FROZEN. No redesign.
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable, Awaitable
from pydantic import BaseModel, Field

from backend.rag.context_builder import CharacterContext
from backend.cognitive_planning.planner_models import (
    CharacterPlan, CommunicationStyleVector, ResponseStructure,
)
from .llm_provider import get_llm_call

logger = logging.getLogger(__name__)


STYLE_PROMPT_TEMPLATES: Dict[str, str] = {
    "verbosity": (
        "Be {level} verbose in your response.\n"
    ),
    "technical_depth": (
        "Use {level} technical language and terminology.\n"
    ),
    "detail": (
        "Provide {level} detailed explanations.\n"
    ),
    "examples": (
        "Include {level} examples to illustrate points.\n"
    ),
    "curiosity": (
        "Show {level} curiosity and exploration in the response.\n"
    ),
    "precision": (
        "Be {level} precise and exact in your statements.\n"
    ),
    "formality": (
        "Use {level} formal language.\n"
    ),
    "reflection": (
        "Include {level} reflective analysis.\n"
    ),
    "motivation": (
        "Use {level} motivational language.\n"
    ),
    "humor": (
        "Use {level} humor and light-heartedness.\n"
    ),
}

STRUCTURE_PROMPTS: Dict[ResponseStructure, str] = {
    ResponseStructure.TECHNICAL: (
        "Structure your response as a technical analysis with:\n"
        "- Overview of findings\n"
        "- Key evidence and metrics\n"
        "- Analysis of patterns\n"
        "- Conclusion with confidence levels\n"
    ),
    ResponseStructure.CONCISE: (
        "Structure your response concisely:\n"
        "- Direct answer first\n"
        "- Key supporting points\n"
    ),
    ResponseStructure.DEEP_EXPLANATION: (
        "Structure your response as a deep explanation:\n"
        "- Background context\n"
        "- Evidence chain\n"
        "- Analysis and implications\n"
        "- Limitations and uncertainty\n"
    ),
    ResponseStructure.COACHING: (
        "Structure your response as coaching:\n"
        "- Acknowledge current state\n"
        "- Assessment of progress\n"
        "- Specific recommendations\n"
        "- Actionable next steps\n"
        "- Encouragement\n"
    ),
    ResponseStructure.REFLECTIVE: (
        "Structure your response reflectively:\n"
        "- Observations\n"
        "- Patterns noticed\n"
        "- Meaning and significance\n"
        "- Implications going forward\n"
    ),
    ResponseStructure.MOTIVATIONAL: (
        "Structure your response motivationally:\n"
        "- Acknowledge strengths\n"
        "- Highlight opportunities\n"
        "- Encouragement and next steps\n"
    ),
    ResponseStructure.RESEARCH: (
        "Structure your response as research:\n"
        "- Question being addressed\n"
        "- Methodology\n"
        "- Key findings\n"
        "- Analysis and comparison\n"
        "- Conclusion\n"
    ),
}


def _level_label(value: float) -> str:
    if value >= 0.8:
        return "very"
    if value >= 0.5:
        return "moderately"
    if value >= 0.2:
        return "slightly"
    return "minimally"


class VerbalizerPrompt(BaseModel):
    prompt_text: str = Field(..., description="The complete prompt for the LLM")
    system_prompt: str = Field(..., description="System instruction for the LLM")
    context_summary: str = Field(..., description="Summary of what was provided")
    style_instructions: str = Field(..., description="Style instructions")
    token_estimate: int = Field(default=0)
    built_at: datetime = Field(default_factory=datetime.utcnow)


class VerbalizerResponse(BaseModel):
    response_id: str = Field(default_factory=lambda: f"vr_{int(time.time() * 1000000)}")
    content: str = ""
    verbalization_time_ms: float = 0.0
    token_count: int = 0
    success: bool = False
    error: Optional[str] = None


class LLMVerbalizer:
    def __init__(
        self,
        llm_call: Optional[Callable[..., Awaitable[str]]] = None,
        config: Optional[dict] = None,
    ):
        self.llm_call = llm_call
        self.config = config or {}
        # Provider-agnostic: when unset, each provider call resolves its own
        # default model (see llm_provider). Avoids sending a gpt-* id to Claude.
        self.model = self.config.get("model") or os.getenv("LLM_MODEL") or None
        self.max_tokens = self.config.get("max_tokens", 2048)
        self.temperature = self.config.get("temperature", 0.7)

    async def verbalize(
        self,
        context: CharacterContext,
        plan: CharacterPlan,
    ) -> VerbalizerResponse:
        start = time.perf_counter()
        try:
            prompt = self._build_prompt(context, plan)
            content = ""

            if self.llm_call:
                try:
                    content = await self.llm_call(
                        system_prompt=prompt.system_prompt,
                        user_prompt=prompt.prompt_text,
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                except Exception as e:
                    # Missing API key, network error, unavailable SDK — never
                    # return a blank response; fall back to deterministic text
                    # built directly from the character context.
                    logger.warning(
                        "LLM call failed (%s); using deterministic fallback", e
                    )
                    content = ""

            if not content or not content.strip():
                content = self._fallback_verbalization(context, plan)

            elapsed = (time.perf_counter() - start) * 1000
            return VerbalizerResponse(
                content=content,
                verbalization_time_ms=elapsed,
                token_count=len(content.split()),
                success=True,
            )
        except Exception as e:
            logger.error(f"Verbalization failed: {e}", exc_info=True)
            elapsed = (time.perf_counter() - start) * 1000
            return VerbalizerResponse(
                content="",
                verbalization_time_ms=elapsed,
                success=False,
                error=str(e),
            )

    def _build_prompt(self, context: CharacterContext, plan: CharacterPlan) -> VerbalizerPrompt:
        system = self._build_system_prompt(plan)
        style_instr = self._build_style_instructions(plan.response_plan.style_vector)
        context_summary = self._summarize_context(context)

        prompt_parts = [
            "# Character Context",
            "",
            context_summary,
            "",
            "# User Query",
            "",
            plan.intent_plan.primary_question,
            "",
            "# Response Structure",
            "",
            STRUCTURE_PROMPTS.get(
                plan.response_plan.primary_structure,
                "Provide a clear, well-structured response.",
            ),
            "",
            "# Style Instructions",
            "",
            style_instr,
            "",
            "# Instructions",
            "",
            "- Use ONLY the information provided above.",
            "- Do NOT add external knowledge or assumptions.",
            "- Do NOT reason, infer, or make decisions.",
            "- Present the information clearly following the requested structure.",
            "- Use citations [source_type:source_id] where applicable.",
            "- If uncertainty is indicated, reflect it honestly.",
        ]

        if plan.response_plan.include_uncertainty:
            prompt_parts.extend([
                "",
                "# Uncertainty Domains",
                "",
                "The following areas have higher uncertainty:",
                *[f"- {d}" for d in context.uncertainty_domains],
            ])

        prompt_text = "\n".join(prompt_parts)
        token_est = len(prompt_text.split()) + len(system.split())

        return VerbalizerPrompt(
            prompt_text=prompt_text,
            system_prompt=system,
            context_summary=context_summary,
            style_instructions=style_instr,
            token_estimate=token_est,
        )

    def _build_system_prompt(self, plan: CharacterPlan) -> str:
        return (
            "You are a verbalization layer for an AI cognitive system. "
            "Your ONLY role is to convert structured character context into natural language. "
            "You do NOT reason, infer, make decisions, or plan. "
            "You do NOT add external knowledge. "
            "You do NOT speculate beyond the provided information. "
            "You present the provided character context and plan clearly and readably. "
            f"User intent: {plan.intent_plan.intent_type.value}. "
            f"Reasoning mode: {plan.reasoning_plan.primary_mode.value}. "
            "Respond in the requested structure and style only."
        )

    def _build_style_instructions(self, style: CommunicationStyleVector) -> str:
        parts = []
        for field_name in style.model_fields_set or CommunicationStyleVector.model_fields.keys():
            if not hasattr(style, field_name):
                continue
            value = getattr(style, field_name)
            template = STYLE_PROMPT_TEMPLATES.get(field_name)
            if template and isinstance(value, (int, float)):
                level = _level_label(value)
                parts.append(template.format(level=level))
        return "".join(parts)

    def _summarize_context(self, context: CharacterContext) -> str:
        lines: List[str] = []

        if context.identity_snapshot:
            snap = context.identity_snapshot
            lines.append(f"## Identity Snapshot (v{snap.get('identity_version', '?')})")
            lines.append(f"  Confidence: {snap.get('overall_confidence', 'N/A')}")
            lines.append(f"  Completeness: {snap.get('identity_completeness', 'N/A')}")
            lines.append(f"  Dominant topics: {snap.get('dominant_topics', [])}")
            if snap.get('emerging_topics'):
                lines.append(f"  Emerging topics: {snap['emerging_topics']}")
            if snap.get('declining_topics'):
                lines.append(f"  Declining topics: {snap['declining_topics']}")
            lines.append("")

        if context.self_model:
            sm = context.self_model
            lines.append(f"## Self Model")
            lines.append(f"  Overall confidence: {sm.get('overall_confidence', 'N/A')}")
            lines.append(f"  Strong beliefs: {len(sm.get('strong_beliefs', []))}")
            lines.append(f"  Uncertain beliefs: {len(sm.get('uncertain_beliefs', []))}")
            if sm.get('primary_motivation_belief'):
                lines.append(f"  Primary motivation belief: {sm['primary_motivation_belief']}")
            lines.append("")

        if context.behavior_objects:
            lines.append(f"## Behavior Objects ({len(context.behavior_objects)})")
            for i, bo in enumerate(context.behavior_objects[:5]):
                lines.append(f"  {i+1}. {bo.get('topic', 'unknown')} "
                             f"(confidence={bo.get('confidence_score', 'N/A')}, "
                             f"engagement={bo.get('engagement_statistics', {}).get('overall_engagement_rate', 'N/A')})")
            if len(context.behavior_objects) > 5:
                lines.append(f"  ... and {len(context.behavior_objects) - 5} more")
            lines.append("")

        if context.inferences:
            lines.append(f"## Inferences ({len(context.inferences)})")
            for inf in context.inferences[:5]:
                lines.append(f"  - {inf.get('label', 'unknown')}: "
                             f"{inf.get('description', '')[:100]} "
                             f"(confidence={inf.get('confidence', 'N/A')})")
            lines.append("")

        if context.goals:
            lines.append(f"## Goals ({len(context.goals)})")
            for goal in context.goals[:3]:
                lines.append(f"  - {goal.get('goal_description', goal.get('description', 'unknown'))} "
                             f"[{goal.get('goal_status', 'active')}]")
            lines.append("")

        if context.fused_evidence and context.fused_evidence.facts:
            facts = context.fused_evidence.facts
            lines.append(f"## Fused Evidence ({len(facts)} facts)")
            lines.append(f"  Aggregate confidence: {context.fused_evidence.aggregate_confidence:.2f}")
            for fact in facts[:5]:
                lines.append(f"  - [{fact.source_type}] {fact.claim[:120]}")
            lines.append("")

        return "\n".join(lines)

    def _fallback_verbalization(self, context: CharacterContext, plan: CharacterPlan) -> str:
        lines: List[str] = []
        intent = plan.intent_plan

        if intent.intent_type.value == "identity_question":
            lines.append("Based on your identity profile:")
            if context.identity_snapshot:
                snap = context.identity_snapshot
                topics = snap.get("dominant_topics", [])
                conf = snap.get("overall_confidence", 0)
                lines.append(f"- Your dominant interests are: {', '.join(topics[:5])}")
                lines.append(f"- Identity confidence: {conf:.2f}")
            return "\n".join(lines)

        if intent.intent_type.value == "behavioral_question":
            lines.append("Based on your behavioral data:")
            for bo in context.behavior_objects[:5]:
                lines.append(
                    f"- {bo.get('topic', 'unknown')}: "
                    f"{bo.get('temporal_statistics', {}).get('occurrence_count', 0)} interactions"
                )
            return "\n".join(lines)

        lines.append(f"Here is what I found about '{intent.primary_question}':")
        if context.fused_evidence:
            for fact in context.fused_evidence.facts[:3]:
                lines.append(f"- {fact.claim}")
        if context.overall_confidence < 0.5:
            lines.append("\nNote: Confidence in this information is limited.")
        return "\n".join(lines)


_verbalizer_instance: Optional[LLMVerbalizer] = None


def get_verbalizer(config: Optional[dict] = None) -> LLMVerbalizer:
    global _verbalizer_instance
    if _verbalizer_instance is None:
        llm_call = get_llm_call()
        cfg = config or {}
        _verbalizer_instance = LLMVerbalizer(llm_call=llm_call, config=cfg)
    return _verbalizer_instance
