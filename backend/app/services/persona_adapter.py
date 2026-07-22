"""
PersonaAdapter — Legacy V2 Compatibility Wrapper

Wraps V3 Identity data into V2 Persona format for backward compatibility.
No duplicate logic. No separate Persona pipeline.
Identity is the canonical user representation.
Persona is derived from Identity data on demand.
"""
import logging
from typing import Dict, Any, Optional, List

from backend.identity.identity_engine import Identity
from app.db.postgres import fetch, fetchrow, execute

logger = logging.getLogger(__name__)


def identity_to_persona(identity: Identity) -> Dict[str, Any]:
    """
    Convert V3 Identity to V2 Persona format.
    
    This is the ONLY place that produces Persona data.
    No separate Persona computation exists.
    """
    # Derive archetype from motivation signals
    signals = identity.motivation_signals
    archetype, traits = _derive_archetype(signals, identity.behavior_profile)
    
    # Map interest graph to interest vector
    interest_vector = {
        "top_topics": [n.topic for n in identity.interest_graph.dominant_interests[:5]],
        "topic_count": identity.interest_graph.total_topics,
    }
    
    # Map behavior profile to behavior vector
    bp = identity.behavior_profile
    behavior_vector = {
        "avg_watch_time": bp.avg_watch_time,
        "total_watch_time": bp.total_events * bp.avg_watch_time,
        "total_events": bp.total_events,
        "top_creators": [n.creator for n in identity.creator_graph.top_creators[:5]],
    }
    
    return {
        "persona_label": archetype["label"],
        "description": archetype["description"],
        "traits": traits,
        "interest_vector": interest_vector,
        "behavior_vector": behavior_vector,
        "strengths": archetype["strengths"],
        "weaknesses": archetype["weaknesses"],
        "recommendations": archetype["recommendations"],
        "confidence": round(identity.overall_confidence, 3),
        "identity_version": identity.identity_version,
        "identity_id": identity.identity_id,
    }


def _derive_archetype(signals, bp) -> tuple:
    """Derive archetype from V3 identity signals"""
    learning = signals.learning_motivation
    entertainment = signals.entertainment_seeking
    curiosity = signals.curiosity_score
    exploration_rate = bp.behavior_diversity
    consistency = bp.behavior_stability
    
    traits = {
        "attention_score": round(min(1.0, bp.avg_watch_time / 30.0), 3),
        "engagement_score": round(bp.avg_engagement_rate, 3),
        "content_diversity": round(exploration_rate, 3),
        "curiosity_score": round(curiosity, 3),
        "learning_motivation": round(learning, 3),
        "consistency": round(consistency, 3),
    }
    
    if learning > 0.6 and consistency > 0.5:
        return {
            "label": "Focused Learner",
            "description": "Deeply engages with specific educational content",
            "strengths": ["Deep focus", "Goal-oriented", "Knowledge building"],
            "weaknesses": ["Narrow perspective", "Limited variety"],
            "recommendations": [
                "Explore adjacent topics to broaden perspective",
                "Mix entertainment content for mental refresh",
            ],
        }, traits
    elif curiosity > 0.6 and exploration_rate > 0.5:
        return {
            "label": "Explorer",
            "description": "Actively seeks diverse content across many topics",
            "strengths": ["Open-minded", "Broad knowledge", "Adaptable"],
            "weaknesses": ["Easily distracted", "Shallow engagement"],
            "recommendations": [
                "Try deep-diving into one topic per week",
                "Create a focused watchlist",
            ],
        }, traits
    elif entertainment > 0.6 or (curiosity > 0.5 and consistency < 0.4):
        return {
            "label": "High-Stimulation Seeker",
            "description": "Rapidly engages with stimulating content",
            "strengths": ["Trend-aware", "Quick pattern recognition"],
            "weaknesses": ["Low attention span", "Impulse-driven"],
            "recommendations": [
                "Practice watching full videos before scrolling",
                "Set a daily screen time goal",
            ],
        }, traits
    elif bp.avg_engagement_rate < 0.3 and consistency < 0.4:
        return {
            "label": "Passive Consumer",
            "description": "Casually scrolls without strong engagement",
            "strengths": ["Relaxed approach", "Low-stress consumption"],
            "weaknesses": ["Low intentionality", "Time sink risk"],
            "recommendations": [
                "Define what you want from social media",
                "Curate your feed around your interests",
            ],
        }, traits
    else:
        return {
            "label": "Balanced User",
            "description": "Developing unique behavioral patterns",
            "strengths": ["Adaptable", "Growing"],
            "weaknesses": ["Pattern not yet established"],
            "recommendations": [
                "Continue using the platform to build a behavioral profile",
            ],
        }, traits
