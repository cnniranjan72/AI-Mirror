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
from .llm_provider import get_llm_call, resolve_provider, DEFAULT_MODEL_BY_PROVIDER

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
    used_fallback: bool = False
    error: Optional[str] = None
    # Which LLM actually produced `content` — "fallback" (not a real vendor
    # name) when used_fallback is True, so downstream consumers never claim
    # a specific model answered when the deterministic template did.
    provider: Optional[str] = None
    model: Optional[str] = None


class LLMVerbalizer:
    def __init__(
        self,
        llm_call: Optional[Callable[..., Awaitable[str]]] = None,
        config: Optional[dict] = None,
    ):
        self.llm_call = llm_call
        self.config = config or {}
        # Which provider llm_call actually calls — resolved the same way
        # get_llm_call() picks the function, so this is never guessed.
        self.provider = resolve_provider(self.config.get("provider"))
        # Provider-agnostic: when unset, each provider call resolves its own
        # default model (see llm_provider). Avoids sending a gpt-* id to Claude.
        self.model = self.config.get("model") or os.getenv("LLM_MODEL") or DEFAULT_MODEL_BY_PROVIDER[self.provider]
        self.max_tokens = self.config.get("max_tokens", 2048)
        self.temperature = self.config.get("temperature", 0.7)
        # Circuit breaker: after an unrecoverable LLM error (bad key, no billing)
        # stop calling the LLM for the rest of the process so every subsequent
        # request serves the deterministic fallback instantly instead of waiting
        # ~20s for the provider to reject it again. Cleared on restart.
        self._llm_disabled = False
        self._llm_disabled_reason: Optional[str] = None
        # Actual outcomes. The circuit breaker alone is not a status signal:
        # it only trips on errors in _FATAL_LLM_ERRORS, so a provider failing
        # every single call for a non-fatal reason (network, transient quota)
        # falls back silently and leaves the breaker closed. Reporting the
        # breaker as availability therefore claimed the LLM was working while
        # every answer was deterministic.
        self._llm_attempts = 0
        self._llm_last_ok: Optional[bool] = None
        self._llm_last_error: Optional[str] = None

    _FATAL_LLM_ERRORS = (
        "insufficient_quota", "authentication", "invalid_api_key",
        "invalid api key", "401", "permission",
    )

    async def verbalize(
        self,
        context: CharacterContext,
        plan: CharacterPlan,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        override: Optional[Dict[str, Any]] = None,
    ) -> VerbalizerResponse:
        """override (from user_llm_config.get_resolved_llm_config): when a
        user has their own provider/key configured via /settings/llm, use
        it for this call instead of the server-wide default. None (the
        common case — no override configured) behaves exactly as before."""
        start = time.perf_counter()
        try:
            prompt = self._build_prompt(context, plan, conversation_history)
            content = ""

            call_provider = self.provider
            call_model = self.model
            call_kwargs = {}
            llm_call = self.llm_call
            if override and override.get("provider"):
                llm_call = get_llm_call(override["provider"])
                call_provider = resolve_provider(override["provider"])
                call_model = override.get("model") or DEFAULT_MODEL_BY_PROVIDER[call_provider]
                call_kwargs = {"api_key": override.get("api_key")}
                # base_url is only a valid kwarg for ollama_call — the other
                # providers don't accept one and would raise a TypeError.
                if call_provider == "ollama" and override.get("base_url"):
                    call_kwargs["base_url"] = override["base_url"]

            if llm_call and not self._llm_disabled:
                self._llm_attempts += 1
                try:
                    content = await llm_call(
                        system_prompt=prompt.system_prompt,
                        user_prompt=prompt.prompt_text,
                        model=call_model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        **call_kwargs,
                    )
                    self._llm_last_ok = bool(content and content.strip())
                    if not self._llm_last_ok:
                        self._llm_last_error = "provider returned an empty response"
                except Exception as e:
                    self._llm_last_ok = False
                    self._llm_last_error = str(e)[:200]
                    # Missing API key, network error, unavailable SDK — never
                    # return a blank response; fall back to deterministic text
                    # built directly from the character context.
                    logger.warning(
                        "LLM call failed (%s); using deterministic fallback", e
                    )
                    content = ""
                    msg = str(e).lower()
                    if any(s in msg for s in self._FATAL_LLM_ERRORS):
                        self._llm_disabled = True
                        self._llm_disabled_reason = str(e)[:200]
                        logger.error(
                            "Disabling LLM verbalization for this process "
                            "(fix the provider account, then restart): %s",
                            self._llm_disabled_reason,
                        )

            used_fallback = False
            if not content or not content.strip():
                content = self._fallback_verbalization(context, plan)
                used_fallback = True

            elapsed = (time.perf_counter() - start) * 1000
            return VerbalizerResponse(
                content=content,
                verbalization_time_ms=elapsed,
                token_count=len(content.split()),
                success=True,
                used_fallback=used_fallback,
                # "fallback" (not a vendor name) whenever the deterministic
                # template produced content, since no LLM actually answered.
                provider="fallback" if used_fallback else call_provider,
                model=None if used_fallback else call_model,
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

    def _build_prompt(
        self,
        context: CharacterContext,
        plan: CharacterPlan,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> VerbalizerPrompt:
        system = self._build_system_prompt(plan)
        style_instr = self._build_style_instructions(plan.response_plan.style_vector)
        context_summary = self._summarize_context(context)

        prompt_parts = ["# Character Context", "", context_summary, ""]

        # Prior turns give the character continuity within a conversation.
        if conversation_history:
            prompt_parts.append("# Conversation So Far")
            prompt_parts.append("")
            for turn in conversation_history[-6:]:
                who = "User" if turn.get("role") == "user" else "You"
                text = (turn.get("content") or "").strip().replace("\n", " ")
                if text:
                    prompt_parts.append(f"{who}: {text[:400]}")
            prompt_parts.append("")

        prompt_parts += [
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
            "- Do NOT reason, infer, or make decisions — that has already been done upstream.",
            "- Present the information clearly following the requested structure.",
            "- Use citations [source_type:source_id] where applicable.",
            "- If uncertainty is indicated, reflect it honestly.",
            "- Format for readability: start with a ONE-SENTENCE direct answer, then "
            "back it up with 2-5 short bullet points citing the specific evidence/topics/"
            "confidence numbers from the context above. Keep it skimmable, not a wall of text.",
            "- Do NOT invent follow-up questions or next steps yourself — those are handled separately.",
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

    def phrasing_status(self) -> Dict[str, Any]:
        """Whether the language model is actually phrasing answers right now.

        The circuit breaker already records this precisely — it flips on a
        fatal provider error (bad key, exhausted quota) and keeps the reason —
        but nothing ever surfaced it. Meanwhile Settings told users they were
        "using the server's shared key", which reads as a working feature. On
        this deployment every answer has been deterministic for the whole of
        its life, and no user could have known why.

        Deliberately reports the ABSENCE of phrasing as a mode, not a fault:
        the deterministic answer is the product's actual claim, and the model
        is a presentation layer over it.
        """
        if self._llm_disabled:
            state, available, reason = "unavailable", False, self._llm_disabled_reason
        elif self._llm_attempts == 0:
            # Nothing has exercised the provider yet on this process, so any
            # claim either way would be a guess. Reported as unknown rather
            # than optimistically available.
            state, available, reason = "unknown", None, None
        elif self._llm_last_ok:
            state, available, reason = "available", True, None
        else:
            state, available, reason = "unavailable", False, self._llm_last_error

        return {
            "provider": resolve_provider(),
            "state": state,
            # None means "not yet known" — callers must not treat that as true.
            "llm_phrasing_available": available,
            "attempts": self._llm_attempts,
            # Truncated: provider errors can echo request details, and this
            # endpoint is readable without authentication.
            "disabled_reason": (reason or None) and str(reason)[:200],
            "answers_are_deterministic": available is False,
        }

    def _audit_answer_lines(self, context: CharacterContext, intent) -> List[str]:
        """Answer an audit question from pre-computed findings, no LLM involved.

        Returns [] when the question is not about an audit, or when the
        relevant scorer declined to judge — in which case the caller falls
        through to the ordinary evidence answer rather than this one asserting
        anything.
        """
        kind = _audit_question_kind(getattr(intent, "primary_question", "") or "")
        if not kind:
            return []

        lines: List[str] = []

        if kind == "provenance":
            prov = context.interest_provenance or {}
            if not prov.get("topics"):
                return []
            if not prov.get("measurable"):
                return [
                    "- I can't tell yet. Deciding whether an interest was chosen or fed "
                    "needs evidence of you seeking it out - searches, likes, saves - and "
                    "there isn't enough of that in your imported history.",
                    "- Importing a Google Takeout export that includes search history "
                    "would make this measurable.",
                ]
            summary = prov.get("summary", {})
            share = summary.get("fed_share_of_attention")
            if share is not None:
                lines.append(
                    f"- {round(share * 100)}% of your judged watching went to topics with no "
                    f"evidence you ever sought them out."
                )
            for t in (prov.get("topics") or []):
                if t.get("verdict") == "fed":
                    lines.append(
                        f"- {t.get('topic')}: fed to you - {t.get('exposure')} views, "
                        f"{t.get('searches')} searches."
                    )
            for t in (prov.get("topics") or []):
                if t.get("verdict") == "chosen":
                    lines.append(
                        f"- {t.get('topic')}: chosen - {t.get('searches')} searches behind "
                        f"{t.get('exposure')} views."
                    )
            return lines[:8]

        audit = context.platform_audit or {}
        if not audit.get("claims_total"):
            return []
        if not audit.get("verdict_reliable"):
            return [
                f"- {audit['claims_total']} ad-targeting claims were imported, but there "
                f"isn't enough of your behaviour recorded yet to test whether they're true.",
            ]
        summary = audit.get("summary", {})
        share = summary.get("supported_share")
        if share is not None:
            lines.append(
                f"- {round(share * 100)}% of their testable claims about you are supported "
                f"by your actual behaviour."
            )
        unsupported = [c.get("label") for c in (audit.get("unsupported") or [])[:5]]
        if unsupported:
            lines.append(f"- Targeted on, with no support in your history: {', '.join(unsupported)}.")
        missed = [m.get("topic") for m in (audit.get("missed") or [])[:5]]
        if missed:
            lines.append(f"- Well-evidenced interests they never target: {', '.join(missed)}.")
        return lines[:8]

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

        # Audit findings. Stated as measured facts with their numbers attached,
        # and only when their own scorer said the verdict was reliable — the
        # model is being handed a conclusion to phrase, not evidence to reason
        # over. Where a scorer declined to judge, that refusal is passed through
        # verbatim so chat cannot be more confident than the Report.
        audit = context.platform_audit or {}
        if audit.get("claims_total"):
            lines.append("## Platform profile audit (measured, not inferred)")
            if not audit.get("verdict_reliable"):
                lines.append(
                    f"  {audit['claims_total']} ad-interest claims were imported, but there is "
                    f"NOT enough behavioural data to judge them. Say so; do not evaluate them."
                )
            else:
                summ = audit.get("summary", {})
                share = summ.get("supported_share")
                lines.append(
                    f"  {audit['claims_total']} claims imported; "
                    f"{summ.get('corroborated', 0)} corroborated, "
                    f"{summ.get('unsupported', 0)} unsupported by this user's behaviour, "
                    f"{summ.get('not_comparable', 0)} not testable."
                )
                if share is not None:
                    lines.append(f"  {round(share * 100)}% of testable claims are supported.")
                unsupported = [c.get("label") for c in (audit.get("unsupported") or [])[:6]]
                if unsupported:
                    lines.append(f"  Targeted on, with no support found: {', '.join(unsupported)}")
                missed = [m.get("topic") for m in (audit.get("missed") or [])[:6]]
                if missed:
                    lines.append(f"  Well-evidenced interests they never target: {', '.join(missed)}")
            lines.append("")

        prov = context.interest_provenance or {}
        if prov.get("topics"):
            lines.append("## Interest provenance (measured, not inferred)")
            if not prov.get("measurable"):
                lines.append(
                    "  There is NOT enough deliberate-signal data (searches, likes, saves) to "
                    "tell whether interests were chosen or fed. Say that plainly if asked; "
                    "never guess that something was fed."
                )
            else:
                summ = prov.get("summary", {})
                fed_share = summ.get("fed_share_of_attention")
                if fed_share is not None:
                    lines.append(
                        f"  {round(fed_share * 100)}% of judged watching went to topics with no "
                        f"evidence the user ever sought them out."
                    )
                for t in (prov.get("topics") or [])[:6]:
                    if t.get("verdict") == "unknown":
                        continue
                    lines.append(
                        f"  - {t.get('topic')}: {t.get('verdict')} "
                        f"({t.get('exposure')} views, {t.get('searches')} searches)"
                    )
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

    @staticmethod
    def _as_dict(v: Any) -> Dict[str, Any]:
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                d = json.loads(v)
                return d if isinstance(d, dict) else {}
            except Exception:
                return {}
        return {}

    def _fact_lines(self, context: CharacterContext, limit: int = 5) -> List[str]:
        lines: List[str] = []
        if context.fused_evidence and context.fused_evidence.facts:
            for fact in context.fused_evidence.facts[:limit]:
                lines.append(f"- {fact.claim}")
        elif context.evidence:
            for ev in context.evidence[:limit]:
                claim = ev.get("claim") or ev.get("description") or ev.get("evidence_type", "evidence")
                lines.append(f"- {claim}")
        return lines

    def _fallback_verbalization(self, context: CharacterContext, plan: CharacterPlan) -> str:
        lines: List[str] = []
        intent = plan.intent_plan
        snap = context.identity_snapshot or {}
        topics = context.dominant_topics or snap.get("dominant_topics", []) or []
        conf = context.overall_confidence or snap.get("overall_confidence", 0) or 0

        if intent.intent_type.value == "identity_question":
            lines.append("Based on your identity profile:")
            if topics:
                lines.append(f"- Your dominant interests are: {', '.join(map(str, topics[:5]))}")
            emerging = context.emerging_topics or snap.get("emerging_topics", [])
            if emerging:
                lines.append(f"- Emerging interests: {', '.join(map(str, emerging[:3]))}")
            lines.append(f"- Identity confidence: {float(conf):.0%}")
            facts = self._fact_lines(context, 3)
            if facts:
                lines.append("\nSupporting evidence:")
                lines.extend(facts)
            return "\n".join(lines)

        if intent.intent_type.value == "behavioral_question":
            lines.append("Based on your behavioral data:")
            shown = 0
            for bo in context.behavior_objects[:6]:
                topic = bo.get("topic", "unknown")
                temporal = self._as_dict(bo.get("temporal_statistics"))
                engagement = self._as_dict(bo.get("engagement_statistics"))
                count = temporal.get("occurrence_count") or bo.get("occurrence_count") or 0
                rate = engagement.get("overall_engagement_rate")
                detail = f"{count} interactions"
                if isinstance(rate, (int, float)):
                    detail += f", {rate:.0%} engagement"
                lines.append(f"- {topic}: {detail}")
                shown += 1
            if shown == 0:
                # No behavior objects reached the context — ground the answer in
                # the evidence facts instead of returning a bare header.
                lines.extend(self._fact_lines(context, 5) or ["- Not enough behavioral data yet."])
            return "\n".join(lines)

        # Audit findings answer the question directly and are already fully
        # computed, so they lead. This path runs with NO language model: for a
        # product whose claim is that the deterministic pipeline decides, a
        # finding that only surfaces when an LLM happens to be configured would
        # have the dependency exactly backwards.
        audit_lines = self._audit_answer_lines(context, intent)
        if audit_lines:
            lines.append(f"Here is what I found about '{intent.primary_question}':")
            lines.extend(audit_lines)
            return "\n".join(lines)

        lines.append(f"Here is what I found about '{intent.primary_question}':")
        facts = self._fact_lines(context, 4)
        if facts:
            lines.extend(facts)
        elif topics:
            lines.append(f"- Your activity centers on: {', '.join(map(str, topics[:5]))}")
        if float(conf) < 0.5:
            lines.append("\nNote: Confidence in this information is limited by the amount of data collected so far.")
        return "\n".join(lines)


def _audit_question_kind(question: str) -> Optional[str]:
    """Which audit, if either, a question is actually asking about.

    Keyword matching rather than an LLM classifier on purpose: this decides
    whether to state a measured finding, and that decision has to be as
    deterministic as the finding itself.
    """
    q = (question or "").lower()
    provenance_words = (
        "fed", "feed", "chose", "chosen", "choose", "sought", "seek", "searched",
        "algorithm", "manipulat", "pushed", "my own", "genuine",
    )
    platform_words = (
        "ad", "ads", "advertis", "target", "profile", "meta", "instagram", "google",
        "think i", "thinks i", "know about me", "claim",
    )
    if any(w in q for w in provenance_words):
        return "provenance"
    if any(w in q for w in platform_words):
        return "platform"
    return None


_verbalizer_instance: Optional[LLMVerbalizer] = None


def get_verbalizer(config: Optional[dict] = None) -> LLMVerbalizer:
    global _verbalizer_instance
    if _verbalizer_instance is None:
        llm_call = get_llm_call()
        cfg = config or {}
        _verbalizer_instance = LLMVerbalizer(llm_call=llm_call, config=cfg)
    return _verbalizer_instance
