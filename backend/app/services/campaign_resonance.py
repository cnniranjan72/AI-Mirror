"""
Campaign resonance simulator — for the ad/marketing-outreach persona: given a
hypothetical product, content, or campaign description, score how well it
resonates with a user's real algorithmic identity BEFORE spending on outreach.

Deterministic, rule-based keyword/overlap scoring against real identity
fields (dominant topics, creator affinity, motivation signals) — no LLM
involved, consistent with the platform's "LLM never reasons or decides"
architecture principle. Every point in the score cites what produced it.
"""
import json
import logging
import re
from typing import Any, Dict, List

from app.db.postgres import fetch, fetchrow

logger = logging.getLogger(__name__)

# Keyword buckets mapped to MotivationSignals dimensions — deliberately small
# and literal (substring/word match only) rather than any NLP model.
MOTIVATION_KEYWORDS = {
    "learning_motivation": {"learn", "course", "tutorial", "guide", "howto", "lesson", "class", "education", "teach"},
    "entertainment_seeking": {"fun", "meme", "comedy", "entertainment", "viral", "funny", "game", "prank"},
    "skill_building_intent": {"build", "create", "pro", "advanced", "master", "certification", "project", "portfolio"},
    "curiosity_score": {"new", "discover", "explore", "secret", "hidden", "insight", "behind", "why", "how"},
}


def _j(v, default):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return default
    return v if v is not None else default


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


async def score_campaign(user_id: str, campaign_text: str) -> Dict[str, Any]:
    identity = await fetchrow(
        "SELECT dominant_topics, emerging_topics, motivation_signals, creator_graph, overall_confidence "
        "FROM identities WHERE user_id = $1",
        user_id,
    )
    if not identity:
        return {"error": "no identity available for this user yet"}

    bo_rows = await fetch(
        "SELECT topic, creators, importance_score FROM behavior_objects WHERE user_id = $1 "
        "ORDER BY importance_score DESC LIMIT 30",
        user_id,
    )

    words = _tokenize(campaign_text)

    dominant_topics = _j(identity["dominant_topics"], [])
    emerging_topics = _j(identity["emerging_topics"], [])
    motivation = _j(identity["motivation_signals"], {})
    creator_graph = _j(identity["creator_graph"], {})

    # Topic overlap — does the campaign text mention (substring, either
    # direction) any of the user's real dominant/emerging topics?
    topic_matches = []
    for t in dominant_topics + emerging_topics:
        t_norm = t.lower().replace("content by ", "").strip()
        if not t_norm:
            continue
        if any(t_norm in w or w in t_norm for w in words if len(w) > 2):
            topic_matches.append(t)
    topic_matches = list(dict.fromkeys(topic_matches))  # de-dupe, preserve order
    topic_score = min(1.0, len(topic_matches) / max(len(dominant_topics), 1))

    # Creator affinity — does the campaign mention creators this user
    # actually engages with?
    all_creators: List[str] = []
    creator_importance: Dict[str, float] = {}
    for r in bo_rows:
        for c in _j(r["creators"], []):
            if c not in all_creators:
                all_creators.append(c)
                creator_importance[c] = float(r["importance_score"] or 0)
    creator_matches = [
        c for c in all_creators
        if c.lower().replace("@", "").replace("_", "") in {w.replace("_", "") for w in words}
        or any(c.lower().replace("@", "") in w for w in words if len(w) > 3)
    ]
    creator_score = min(1.0, len(creator_matches) / 3) if all_creators else 0.0

    # Motivation alignment — which motivational dimensions does the
    # campaign's language actually speak to, and how strong is that
    # dimension for this user?
    triggered_dims = {dim for dim, kws in MOTIVATION_KEYWORDS.items() if words & kws}
    motivation_alignment = {
        dim: round(float(motivation.get(dim, 0.0)), 3)
        for dim in triggered_dims
    }
    motivation_score = (
        sum(motivation_alignment.values()) / len(motivation_alignment)
        if motivation_alignment else 0.0
    )

    overall = round(topic_score * 0.4 + creator_score * 0.25 + motivation_score * 0.35, 3)

    explanation = []
    if topic_matches:
        explanation.append(f"Mentions {len(topic_matches)} of this user's real interest topics: {', '.join(topic_matches[:5])}.")
    else:
        explanation.append("No overlap with this user's dominant or emerging topics.")
    if creator_matches:
        explanation.append(f"References creator(s) this user actually engages with: {', '.join(creator_matches[:3])}.")
    if motivation_alignment:
        top_dim = max(motivation_alignment, key=motivation_alignment.get)
        explanation.append(f"Language matches '{top_dim.replace('_', ' ')}' — this user scores {round(motivation_alignment[top_dim]*100)}% on that dimension.")
    else:
        explanation.append("Campaign language doesn't clearly speak to any tracked motivation dimension.")

    return {
        "resonance_score": overall,
        "resonance_pct": round(overall * 100),
        "breakdown": {
            "topic_overlap": round(topic_score, 3),
            "creator_affinity": round(creator_score, 3),
            "motivation_alignment": round(motivation_score, 3),
        },
        "topic_matches": topic_matches,
        "creator_matches": creator_matches,
        "motivation_alignment": motivation_alignment,
        "explanation": explanation,
        "identity_confidence": float(identity["overall_confidence"] or 0),
        "method": "deterministic keyword/overlap scoring against real identity fields — no LLM involved",
    }
