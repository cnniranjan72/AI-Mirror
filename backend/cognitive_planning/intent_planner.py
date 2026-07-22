"""
Intent Planner — Rule-Based Intent Classification

Determines user intent from query text.
No LLM. Rule-based pattern matching.
Architecture V3 — FROZEN. No redesign.
"""
import re
import logging
from typing import List, Optional, Set, Dict, Tuple
from .planner_models import (
    UserIntentType, IntentPlan, CommunicationStyleVector, ResponseStructure
)

logger = logging.getLogger(__name__)

_INTENT_PRIORITY: Dict[UserIntentType, int] = {
    UserIntentType.MEMORY_QUESTION: 10,
    UserIntentType.EXPLANATION: 9,
    UserIntentType.COMPARISON: 8,
    UserIntentType.PREDICTION: 7,
    UserIntentType.BEHAVIORAL_QUESTION: 6,
    UserIntentType.REFLECTION: 5,
    UserIntentType.RECOMMENDATION: 4,
    UserIntentType.COACHING: 3,
    UserIntentType.IDENTITY_QUESTION: 2,
    UserIntentType.INFORMATION: 1,
}

_MAX_CONFIDENCE_MATCHES = 3


class IntentPlanner:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.min_confidence = self.config.get("min_confidence", 0.3)
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        self._patterns: Dict[UserIntentType, List[re.Pattern]] = {
            UserIntentType.EXPLANATION: [
                re.compile(r"\bwhy (did|does|is|are|would|should|do|keep|have|has|had)\b", re.I),
                re.compile(r"\b(reason for|cause of|why is it that|how come)\b", re.I),
                re.compile(r"\b(explain why|explain how|what causes|what caused)\b", re.I),
                re.compile(r"\b(reasons why|factors (behind|that)|led to)\b", re.I),
                re.compile(r"\bwhy (is|are|has|have|had|would|do|does|did) .{3,40}? (chang\w*|happened?|occur\w*|stop\w*|start\w*|shift\w*)\b", re.I),
                re.compile(r"\b(what changed|what shifted|what happened) (to|with) (my|the)\b", re.I),
            ],
            UserIntentType.REFLECTION: [
                re.compile(r"\b(reflect|reflecting|looking back|looking at)\b", re.I),
                re.compile(r"\b(lately|these days|i've been (thinking|noticing|learning|feeling))\b", re.I),
                re.compile(r"\b(what (have|am) I (been|learning|doing|feeling|watching))\b", re.I),
                re.compile(r"\b(evolv\w*|chang\w*|develop\w*|progress\w*|grow\w*)\b", re.I),
                re.compile(r"\b(my .{1,40}? (evolv\w*|chang\w*|progress\w*|develop\w*|grow\w*))\b", re.I),
                re.compile(r"\b(what have I been (noticing|observing|learning|realizing|feeling))\b", re.I),
                re.compile(r"\bhow (has|have) my (interest|learning|habit|taste|preference)s?\b", re.I),
                re.compile(r"\b(i (used to|would|notice|feel|think|wonder))\b", re.I),
                re.compile(r"\b(my (thoughts|feelings|experience|journey|progress|evolution))\b", re.I),
            ],
            UserIntentType.IDENTITY_QUESTION: [
                re.compile(r"\b(who am I|what am I|about me)\b", re.I),
                re.compile(r"\b(what kind of (person|learner|viewer|consumer|am))\b", re.I),
                re.compile(r"\b(what type of (person|learner|viewer|consumer))\b", re.I),
                re.compile(r"\b(kind of .+ am I|type of .+ am I)\b", re.I),
                re.compile(r"\bmy (\w+ )?(interests|preferences|identity|personality)\b", re.I),
                re.compile(r"\b(describe me|my profile|my identity|who I am)\b", re.I),
                re.compile(r"\bwhat sort of\b", re.I),
                re.compile(r"\b(what are my (core |main |primary )?(interests|traits|characteristics))\b", re.I),
            ],
            UserIntentType.BEHAVIORAL_QUESTION: [
                re.compile(r"\b(how (much|often|frequently|long) (do I|have I|did I|am I))\b", re.I),
                re.compile(r"\b(my (\w+ )?(habits|behavior|pattern|patterns|routine|tendency|tendencies))\b", re.I),
                re.compile(r"\b((what|which) \w+ (influence|affect|shape)s? (me|my))\b", re.I),
                re.compile(r"\b(what (content|videos|topics|creators|channels) (do I|have I|am I|did I))\b", re.I),
                re.compile(r"\b(watch (time|history|pattern)|browsing|scrolling|viewing)\b", re.I),
                re.compile(r"\bwho (influences|affects|shapes) (me|my)\b", re.I),
                re.compile(r"\b(who \S+ (influences|affects|shapes) (me|my))\b", re.I),
                re.compile(r"\b(my (top|favorite|most) (content|topics|creators|watched|viewed))\b", re.I),
                re.compile(r"\b(what are my .{1,30} (patterns|habits|behaviors|routines))\b", re.I),
                re.compile(r"\bhow (much|many) (time|hours|days|minutes) (do I|have I|did I|am I)\b", re.I),
            ],
            UserIntentType.MEMORY_QUESTION: [
                re.compile(r"\b(remember|do you recall|what did I)\b", re.I),
                re.compile(r"\b(earlier|before|previously|last (week|month|time|night|session))\b", re.I),
                re.compile(r"\b(did I (watch|see|view|like|save|skip|click|read))\b", re.I),
                re.compile(r"\b(what was I (watching|doing|learning|viewing))\b", re.I),
                re.compile(r"\b(what (happened|did) (yesterday|last|earlier))\b", re.I),
            ],
            UserIntentType.COMPARISON: [
                re.compile(r"\b(compare|differen\w*|vs\.|versus)\b", re.I),
                re.compile(r"\b(better (than|between)|which (one|is better|is best|should i))\b", re.I),
                re.compile(r"\b(different (from|than)|how (does .+ compare|is .+ different|does .+ differ))\b", re.I),
                re.compile(r"\b(similarities|contrast|rather than|either|prefer)\b", re.I),
                re.compile(r"\b(differ\w* from|differ\w* than)\b", re.I),
            ],
            UserIntentType.PREDICTION: [
                re.compile(r"\b(predict|will I|forecast|future|what if)\b", re.I),
                re.compile(r"\b(trend (for|in)|continue to|what's next for|going to)\b", re.I),
                re.compile(r"\b(how (long|far) (will|until)|likelihood|chance of)\b", re.I),
                re.compile(r"\b(will I (keep|continue|still|ever))\b", re.I),
                re.compile(r"\b(trends? (in|of|for) (my|the))\b", re.I),
                re.compile(r"\bnext (for|in) (my|the)\b", re.I),
            ],
            UserIntentType.COACHING: [
                re.compile(r"\b(help me|advice|how can I improve)\b", re.I),
                re.compile(r"\b(tips (for|on)|recommendation (for|about) my)\b", re.I),
                re.compile(r"\b(strategy|plan|goal|get better at|how to)\b", re.I),
                re.compile(r"\b(improve|achieve|accomplish)\b", re.I),
                re.compile(r"\b(what (should|can) I do (to|about))\b", re.I),
                re.compile(r"\b(tips (for|on|about|do you|can you))\b", re.I),
                re.compile(r"\b(tips (for|on|about) .{1,30} (learning|studying|improving))\b", re.I),
                re.compile(r"\b(how (can|should) I (achieve|reach|accomplish|build|develop))\b", re.I),
                re.compile(r"\b(should I (focus|prioritize|choose|spend|try|do|learn))\b", re.I),
            ],
            UserIntentType.RECOMMENDATION: [
                re.compile(r"\b(recommend|suggest|what should I (watch|read|learn|do))\b", re.I),
                re.compile(r"\b(good (content|video|resource|article|tutorial|channel))\b", re.I),
                re.compile(r"\b(what (else|next)|similar (to|content))\b", re.I),
                re.compile(r"\b(any (good|interesting|recommended|great) .{1,30} (for|about))\b", re.I),
                re.compile(r"\b(what are (some|good|great|the best) .{1,30} (for|about))\b", re.I),
            ],
            UserIntentType.INFORMATION: [
                re.compile(r"\b(tell me about|explain (what|how)|define|describe)\b", re.I),
                re.compile(r"\b(what is|what are|what's|what does|what do|what was|what were)\b", re.I),
                re.compile(r"\b(how (does|do|can|would|should|is|are|has|have|had|did))\b", re.I),
                re.compile(r"\b(meaning of|definition of|overview of|summary of)\b", re.I),
                re.compile(r"\b(what|which) \w+ .{0,40}?\b(mean|means|show|shows|support|supports|indicate|indicates)\b", re.I),
                re.compile(r"\b(what information|what data|what details|how does it)\b", re.I),
            ],
        }

    def classify(self, query: str) -> IntentPlan:
        query_lower = query.strip().lower()
        if not query_lower:
            return self._unknown_plan()

        raw_scores: Dict[UserIntentType, float] = {}
        for intent_type, patterns in self._patterns.items():
            matches = sum(1 for pat in patterns if pat.search(query_lower))
            if matches > 0:
                raw_scores[intent_type] = self._normalize_score(matches)

        if not raw_scores:
            return self._unknown_plan()

        best_intent, best_score = self._resolve_best(raw_scores)

        alternatives = sorted(
            [k for k, v in raw_scores.items() if k != best_intent and v >= best_score * 0.5],
            key=lambda k: raw_scores[k], reverse=True
        )

        ambiguity = 1.0 - best_score if len(raw_scores) > 1 else 0.0
        confidence = best_score * (1.0 - 0.15 * ambiguity)
        confidence = max(0.0, min(1.0, confidence))

        key_entities = self._extract_entities(query_lower)
        key_topics = self._extract_topics(query_lower)
        time_ref = self._extract_time_reference(query_lower)

        return IntentPlan(
            intent_type=best_intent,
            intent_confidence=round(confidence, 4),
            primary_question=query,
            key_entities=key_entities,
            key_topics=key_topics,
            time_reference=time_ref,
            requires_comparison=best_intent == UserIntentType.COMPARISON,
            requires_temporal_analysis=best_intent in (
                UserIntentType.PREDICTION, UserIntentType.REFLECTION),
            requires_identity_access=best_intent in (
                UserIntentType.IDENTITY_QUESTION, UserIntentType.BEHAVIORAL_QUESTION,
                UserIntentType.REFLECTION),
            requires_memory_access=best_intent == UserIntentType.MEMORY_QUESTION,
            requires_behavioral_data=best_intent in (
                UserIntentType.BEHAVIORAL_QUESTION, UserIntentType.PREDICTION,
                UserIntentType.COMPARISON),
            requires_goal_data=best_intent == UserIntentType.COACHING,
            requires_prediction=best_intent == UserIntentType.PREDICTION,
            alternatives=alternatives,
            ambiguity_score=round(ambiguity, 4),
        )

    def _normalize_score(self, match_count: int) -> float:
        return min(1.0, match_count / _MAX_CONFIDENCE_MATCHES)

    def _resolve_best(
        self,
        scores: Dict[UserIntentType, float],
    ) -> Tuple[UserIntentType, float]:
        sorted_intents = sorted(
            scores.keys(),
            key=lambda k: (scores[k], _INTENT_PRIORITY.get(k, 0)),
            reverse=True,
        )

        best = sorted_intents[0]
        best_score = scores[best]

        if len(sorted_intents) > 1:
            runner_up = sorted_intents[1]
            runner_score = scores[runner_up]
            score_gap = best_score - runner_score

            if score_gap < 0.15:
                best_priority = _INTENT_PRIORITY.get(best, 0)
                runner_priority = _INTENT_PRIORITY.get(runner_up, 0)

                if runner_priority > best_priority:
                    best = runner_up
                    best_score = runner_score

        return best, best_score

    def compute_style_vector(self, intent: IntentPlan) -> CommunicationStyleVector:
        base = CommunicationStyleVector()
        mapping = {
            UserIntentType.INFORMATION: {"verbosity": 0.6, "technical_depth": 0.7, "precision": 0.8},
            UserIntentType.RECOMMENDATION: {"verbosity": 0.5, "examples": 0.8, "curiosity": 0.3},
            UserIntentType.EXPLANATION: {"verbosity": 0.7, "technical_depth": 0.6, "detail": 0.8},
            UserIntentType.REFLECTION: {"verbosity": 0.6, "reflection": 0.9, "curiosity": 0.6},
            UserIntentType.COMPARISON: {"verbosity": 0.6, "precision": 0.8, "detail": 0.7},
            UserIntentType.PREDICTION: {"verbosity": 0.5, "curiosity": 0.7, "precision": 0.6},
            UserIntentType.COACHING: {"verbosity": 0.6, "motivation": 0.8, "examples": 0.7},
            UserIntentType.IDENTITY_QUESTION: {
                "verbosity": 0.6, "reflection": 0.8, "curiosity": 0.7},
            UserIntentType.MEMORY_QUESTION: {"verbosity": 0.5, "detail": 0.6, "precision": 0.7},
            UserIntentType.BEHAVIORAL_QUESTION: {
                "verbosity": 0.6, "precision": 0.7, "technical_depth": 0.5},
        }
        overrides = mapping.get(intent.intent_type, {})
        for key, val in overrides.items():
            setattr(base, key, val)
        return base

    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        patterns = [
            re.compile(r"\b(my\s+\w+)\b", re.I),
            re.compile(r"\b(\w+\s+(?:content|video|topic|creator))\b", re.I),
        ]
        for pat in patterns:
            entities.extend(m.group(1) for m in pat.finditer(text))
        return list(set(entities))[:5]

    def _extract_topics(self, text: str) -> List[str]:
        topic_keywords = [
            "ai", "programming", "machine learning", "deep learning",
            "art", "photography", "music", "gaming", "fitness",
            "cooking", "travel", "technology", "science", "career",
            "productivity", "design", "writing", "business",
        ]
        found = [kw for kw in topic_keywords if kw in text.lower()]
        return found[:5]

    def _extract_time_reference(self, text: str) -> Optional[str]:
        time_pats = [
            r"\b(today|yesterday|this week|this month|this year)\b",
            r"\b(last week|last month|last year|last (\d+) days)\b",
            r"\b(past (\d+) (days|weeks|months))\b",
            r"\b(recently|lately|earlier|before|previously)\b",
        ]
        for pat_str in time_pats:
            m = re.search(pat_str, text, re.I)
            if m:
                return m.group(0)
        return None

    def _unknown_plan(self) -> IntentPlan:
        return IntentPlan(
            intent_type=UserIntentType.UNKNOWN,
            intent_confidence=0.0,
            ambiguity_score=1.0,
        )


def get_intent_planner() -> IntentPlanner:
    if not hasattr(get_intent_planner, "_instance"):
        get_intent_planner._instance = IntentPlanner()
    return get_intent_planner._instance
