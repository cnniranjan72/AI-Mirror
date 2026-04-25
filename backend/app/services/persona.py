"""
Persona Engine
Computes interest distribution, attention, engagement, curiosity scores.
Maps users to behavioral archetypes.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from collections import Counter

from app.db.postgres import fetch, fetchrow, execute

logger = logging.getLogger(__name__)

# Archetype definitions
ARCHETYPES = {
    "Explorer": {
        "condition": lambda t: t["content_diversity"] > 0.6 and t["curiosity_score"] > 0.5,
        "description": "Actively seeks diverse content across many topics",
        "strengths": ["Open-minded", "Broad knowledge", "Adaptable"],
        "weaknesses": ["Easily distracted", "Shallow engagement", "FOMO tendency"],
        "recommendations": [
            "Try deep-diving into one topic per week",
            "Create a focused watchlist for your top interest",
            "Set time limits to avoid endless scrolling",
        ],
    },
    "Focused Learner": {
        "condition": lambda t: t["attention_score"] > 0.6 and t["engagement_score"] < 0.5,
        "description": "Deeply engages with specific educational content",
        "strengths": ["Deep focus", "Retention ability", "Goal-oriented"],
        "weaknesses": ["Narrow perspective", "Limited variety", "Burnout risk"],
        "recommendations": [
            "Explore adjacent topics to broaden perspective",
            "Take breaks between learning sessions",
            "Mix entertainment content for mental refresh",
        ],
    },
    "High-Stimulation Seeker": {
        "condition": lambda t: t["curiosity_score"] > 0.6 and t["attention_score"] < 0.4,
        "description": "Rapidly scrolls through stimulating content",
        "strengths": ["Trend-aware", "Quick pattern recognition", "Energetic"],
        "weaknesses": ["Low attention span", "Impulse-driven", "Surface-level engagement"],
        "recommendations": [
            "Practice watching full videos before scrolling",
            "Set a daily screen time goal",
            "Try engaging with longer-form content",
        ],
    },
    "Passive Consumer": {
        "condition": lambda t: t["attention_score"] < 0.4 and t["engagement_score"] < 0.4,
        "description": "Casually scrolls without strong engagement",
        "strengths": ["Relaxed approach", "Low-stress consumption", "Background usage"],
        "weaknesses": ["Low intentionality", "Time sink risk", "Minimal value extraction"],
        "recommendations": [
            "Define what you want to get out of social media",
            "Curate your feed around your interests",
            "Try interactive content like polls or Q&A reels",
        ],
    },
}

DEFAULT_ARCHETYPE = {
    "description": "Developing unique behavioral patterns",
    "strengths": ["Adaptable", "Growing"],
    "weaknesses": ["Pattern not yet established"],
    "recommendations": ["Continue using the platform to build a behavioral profile"],
}


def compute_persona(features: Dict[str, Any], enrichment_topics: List[str] = None) -> Dict[str, Any]:
    """
    Compute persona from behavioral features.

    Args:
        features: output from feature_engineering.compute_features()
        enrichment_topics: topics from enrichment service

    Returns:
        Full persona dictionary
    """
    traits = {
        "attention_score": features.get("attention_score", 0),
        "engagement_score": features.get("engagement_score", 0),
        "content_diversity": features.get("content_diversity", 0),
        "curiosity_score": features.get("curiosity_score", 0),
    }

    # Interest distribution from enrichment topics (preferred over hashtags)
    if enrichment_topics and enrichment_topics != ["general"]:
        interest_vector = {
            "top_topics": enrichment_topics[:5],
            "topic_count": len(enrichment_topics),
        }
    else:
        # Fallback to hashtags
        top_hashtags = features.get("top_hashtags", [])
        interest_vector = {
            "top_topics": [h.lstrip("#") for h in top_hashtags[:5]],
            "topic_count": len(top_hashtags),
        }

    # Behavior vector from watch patterns
    behavior_vector = {
        "avg_watch_time": features.get("avg_watch_time", 0),
        "total_watch_time": features.get("total_watch_time", 0),
        "total_events": features.get("total_events", 0),
        "top_creators": features.get("top_creators", []),
    }

    # Determine archetype
    label = "Emerging User"
    archetype_data = DEFAULT_ARCHETYPE
    confidence = 0.0

    for name, arch in ARCHETYPES.items():
        if arch["condition"](traits):
            label = name
            archetype_data = arch
            confidence = max(traits.values()) if traits.values() else 0
            break

    # Update confidence based on topic count
    topic_count = interest_vector["topic_count"]
    if topic_count > 0:
        confidence = min(1.0, confidence + (topic_count / 3))

    persona = {
        "persona_label": label,
        "traits": traits,
        "interest_vector": interest_vector,
        "behavior_vector": behavior_vector,
        "strengths": archetype_data["strengths"],
        "weaknesses": archetype_data["weaknesses"],
        "recommendations": archetype_data["recommendations"],
        "confidence": round(confidence, 3),
        "description": archetype_data["description"],
    }

    logger.info(f"[PERSONA] persona_label={label} confidence={confidence:.3f} topics={interest_vector['top_topics']}")
    return persona


async def save_persona(user_id: str, persona: Dict[str, Any]) -> int:
    """Save persona snapshot to database."""
    row = await fetchrow(
        """
        INSERT INTO personas (user_id, interest_vector, behavior_vector,
                              persona_label, traits, strengths, weaknesses,
                              recommendations, confidence)
        VALUES ($1, $2::jsonb, $3::jsonb, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8::jsonb, $9)
        RETURNING id
        """,
        user_id,
        json.dumps(persona["interest_vector"]),
        json.dumps(persona["behavior_vector"]),
        persona["persona_label"],
        json.dumps(persona["traits"]),
        json.dumps(persona["strengths"]),
        json.dumps(persona["weaknesses"]),
        json.dumps(persona["recommendations"]),
        persona["confidence"],
    )
    logger.info("Saved persona id=%d for user=%s", row["id"], user_id)
    return row["id"]


async def get_latest_persona(user_id: str) -> Optional[Dict[str, Any]]:
    """Get most recent persona for a user."""
    row = await fetchrow(
        """
        SELECT persona_label, traits, interest_vector, behavior_vector,
               strengths, weaknesses, recommendations, confidence, created_at
        FROM personas
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        user_id,
    )
    if not row:
        return None

    return {
        "persona_label": row["persona_label"],
        "traits": row["traits"],
        "interest_vector": row["interest_vector"],
        "behavior_vector": row["behavior_vector"],
        "strengths": row["strengths"],
        "weaknesses": row["weaknesses"],
        "recommendations": row["recommendations"],
        "confidence": float(row["confidence"]),
        "created_at": row["created_at"].isoformat(),
    }
