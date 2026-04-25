"""
RL-Ready Optimization Layer
Structures system for reinforcement learning without full training.
Provides: compute_alignment(), suggest_action()
"""

import json
import logging
from typing import Dict, List, Any, Optional

from app.db.postgres import fetchrow, fetch, execute

logger = logging.getLogger(__name__)

# Alignment dimensions
ALIGNMENT_DIMENSIONS = {
    "intentionality": {
        "description": "Using the platform with clear purpose",
        "weight": 0.3,
    },
    "diversity": {
        "description": "Consuming varied, balanced content",
        "weight": 0.2,
    },
    "depth": {
        "description": "Engaging deeply rather than surface scrolling",
        "weight": 0.3,
    },
    "wellbeing": {
        "description": "Healthy usage patterns and screen time",
        "weight": 0.2,
    },
}

# Action space
ACTIONS = {
    "reduce_session": {
        "label": "Reduce session length",
        "trigger": lambda s: s.get("avg_watch_time", 0) < 5 and s.get("total_events", 0) > 20,
        "description": "Your sessions are long with quick scrolling. Try shorter, focused sessions.",
    },
    "diversify_content": {
        "label": "Explore new content types",
        "trigger": lambda s: s.get("content_diversity", 0) < 0.3,
        "description": "You're watching very similar content. Explore new creators and topics.",
    },
    "increase_engagement": {
        "label": "Engage more deeply",
        "trigger": lambda s: s.get("attention_score", 0) < 0.3,
        "description": "You're scrolling quickly. Try watching reels fully before moving on.",
    },
    "maintain_balance": {
        "label": "Maintain current balance",
        "trigger": lambda s: s.get("attention_score", 0) > 0.5 and s.get("content_diversity", 0) > 0.4,
        "description": "Your usage is balanced. Keep up the intentional consumption.",
    },
}


def compute_alignment(
    persona: Dict[str, Any],
    features: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute alignment score between user behavior and ideal patterns.

    State = persona vector + behavior stats

    Returns:
        {overall_score, dimensions, state}
    """
    traits = persona.get("traits", {})
    attention = traits.get("attention_score", 0)
    engagement = traits.get("engagement_score", 0)
    diversity = traits.get("content_diversity", 0)
    curiosity = traits.get("curiosity_score", 0)

    # Compute per-dimension alignment
    dimensions = {
        "intentionality": min(attention * 1.5, 1.0),
        "diversity": diversity,
        "depth": min(engagement + attention, 1.0) / 2,
        "wellbeing": 1.0 - min(features.get("total_events", 0) / 50, 1.0),  # penalize very long sessions
    }

    # Weighted overall score
    overall = sum(
        dimensions[dim] * ALIGNMENT_DIMENSIONS[dim]["weight"]
        for dim in dimensions
    )

    # Build state representation (for future RL training)
    state = {
        "persona_vector": [attention, engagement, diversity, curiosity],
        "behavior_stats": {
            "total_events": features.get("total_events", 0),
            "avg_watch_time": features.get("avg_watch_time", 0),
            "total_watch_time": features.get("total_watch_time", 0),
        },
        "alignment_scores": dimensions,
    }

    result = {
        "overall_score": round(overall, 3),
        "dimensions": {k: round(v, 3) for k, v in dimensions.items()},
        "state": state,
    }

    logger.info("Alignment score: %.3f", overall)
    return result


def suggest_action(
    alignment: Dict[str, Any],
    features: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Suggest behavioral action based on current state.

    Action = suggest content shift / usage change
    Reward signal = alignment improvement + engagement quality

    Returns:
        {action, description, expected_reward}
    """
    # Find applicable actions
    applicable = []
    for action_id, action in ACTIONS.items():
        merged = {**features, **alignment.get("dimensions", {})}
        if action["trigger"](merged):
            applicable.append({
                "action_id": action_id,
                "label": action["label"],
                "description": action["description"],
            })

    if not applicable:
        applicable = [{
            "action_id": "maintain_balance",
            "label": ACTIONS["maintain_balance"]["label"],
            "description": ACTIONS["maintain_balance"]["description"],
        }]

    # Pick the top action
    chosen = applicable[0]

    # Estimate expected reward
    overall = alignment.get("overall_score", 0.5)
    expected_reward = round(max(0.1, 1.0 - overall), 3)

    result = {
        "action": chosen,
        "all_suggestions": applicable,
        "expected_reward": expected_reward,
        "current_alignment": alignment.get("overall_score", 0),
    }

    logger.info("Suggested action: %s (expected_reward=%.3f)", chosen["action_id"], expected_reward)
    return result


async def log_action(
    user_id: str,
    action_type: str,
    action_data: Dict[str, Any],
    state: Dict[str, Any],
    reward: float,
) -> int:
    """Log an RL action for future training."""
    row = await fetchrow(
        """
        INSERT INTO actions_log (user_id, action_type, action_data, state, reward)
        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)
        RETURNING id
        """,
        user_id,
        action_type,
        json.dumps(action_data),
        json.dumps(state),
        reward,
    )
    logger.info("Logged RL action id=%d user=%s reward=%.3f", row["id"], user_id, reward)
    return row["id"]


async def get_action_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent actions for a user."""
    rows = await fetch(
        """
        SELECT id, action_type, action_data, state, reward, created_at
        FROM actions_log
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )
    return [
        {
            "id": r["id"],
            "action_type": r["action_type"],
            "action_data": r["action_data"],
            "state": r["state"],
            "reward": float(r["reward"]),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
