"""
Follow-up question generation — deterministic, not LLM-generated.

Consistent with the architecture's core rule (the LLM never reasons or
decides): the NEXT questions a user is likely to want are derived directly
from the cognitive context that was actually retrieved for this turn —
emerging topics, uncertain beliefs, live inferences, declining interests —
not invented by a language model. This keeps suggestions traceable to real
data and avoids the LLM proposing something not grounded in evidence.
"""
from typing import List
from backend.cognitive_planning.planner_models import CharacterPlan, UserIntentType
from backend.rag.context_builder import CharacterContext


def generate_follow_ups(context: CharacterContext, plan: CharacterPlan, limit: int = 4) -> List[str]:
    suggestions: List[str] = []
    intent = plan.intent_plan.intent_type

    # Emerging interests are one of the most naturally engaging follow-ups —
    # "you're starting to like X" invites "tell me more about X".
    if context.emerging_topics:
        t = context.emerging_topics[0]
        suggestions.append(f"I noticed '{t}' is emerging for me — what's driving that?")

    # A live inference is a claim about the user; asking "why" is the most
    # natural explainability follow-up and directly exercises the trace UI.
    if context.inferences:
        label = context.inferences[0].get("label") or context.inferences[0].get("description", "")[:40]
        if label:
            suggestions.append(f"Why do you think I have this pattern: {label}?")

    # Uncertainty domains signal where the model itself is least confident —
    # surfacing them invites the user to help resolve ambiguity.
    if context.uncertainty_domains:
        d = context.uncertainty_domains[0]
        suggestions.append(f"You seem unsure about my {d} — what would help clarify that?")

    # Self-model beliefs: contrast strong vs uncertain.
    sm = context.self_model or {}
    if sm.get("uncertain_beliefs"):
        suggestions.append("What are you least confident about in my profile?")
    elif sm.get("strong_beliefs") and intent != UserIntentType.IDENTITY_QUESTION:
        suggestions.append("What's the strongest belief you hold about me?")

    # Dominant topics not already the focus of this turn — comparison angle.
    if len(context.dominant_topics) >= 2:
        a, b = context.dominant_topics[0], context.dominant_topics[1]
        suggestions.append(f"How does my engagement with {a} compare to {b}?")

    # Intent-specific defaults so there is always something useful, even
    # with a thin context.
    intent_defaults = {
        UserIntentType.IDENTITY_QUESTION: "How confident are you in this identity overall?",
        UserIntentType.BEHAVIORAL_QUESTION: "What behavioral pattern of mine has changed most recently?",
        UserIntentType.RECOMMENDATION: "What's one thing I should do differently based on this?",
        UserIntentType.REFLECTION: "What would my ideal balance of content look like?",
        UserIntentType.COACHING: "What's a realistic first step toward that?",
        UserIntentType.PREDICTION: "What could shift this prediction?",
        UserIntentType.COMPARISON: "What changed between these periods?",
        UserIntentType.MEMORY_QUESTION: "What's the most significant thing you remember about me?",
    }
    if intent in intent_defaults:
        suggestions.append(intent_defaults[intent])

    # Dedup, cap, and never return an empty list.
    seen = set()
    unique = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    if not unique:
        unique = ["What are my main interests right now?", "How has my identity changed recently?"]
    return unique[:limit]
