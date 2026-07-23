"""
Reinforcement-Learning Optimization Layer — online contextual bandit.

The environment is the user's behavioural alignment. Each ingest:
  1. computes the current alignment (state),
  2. REWARDS the previously-suggested action by how much alignment improved
     since it was suggested (closed-loop learning from the environment),
  3. selects the next action epsilon-greedily over learned action-values (Q),
  4. logs the action with the context + baseline alignment for the next step.

State  = alignment dimensions; the contextual "arm" is the weakest dimension.
Action = a behavioural nudge (reduce_session / diversify / engage / maintain).
Reward = normalized alignment improvement after the action (0.5 = no change).
Policy = per-(context, action) Q-value, updated by an incremental-mean rule.
"""

import json
import logging
import os
import random
from typing import Dict, List, Any, Optional

from app.db.postgres import fetchrow, fetch, execute

logger = logging.getLogger(__name__)

EPSILON = float(os.getenv("RL_EPSILON", "0.15"))   # exploration rate
ALPHA_MIN = float(os.getenv("RL_ALPHA_MIN", "0.05"))  # learning-rate floor
Q_INIT = 0.5  # optimistic initial action-value

ALIGNMENT_DIMENSIONS = {
    "intentionality": {"description": "Using the platform with clear purpose", "weight": 0.3},
    "diversity": {"description": "Consuming varied, balanced content", "weight": 0.2},
    "depth": {"description": "Engaging deeply rather than surface scrolling", "weight": 0.3},
    "wellbeing": {"description": "Healthy usage patterns and screen time", "weight": 0.2},
}

ACTIONS = {
    "reduce_session": {
        "label": "Reduce session length",
        "trigger": lambda s: s.get("avg_watch_time", 0) < 5 and s.get("total_events", 0) > 20,
        "description": "Your sessions are long with quick scrolling. Try shorter, focused sessions.",
    },
    "diversify_content": {
        "label": "Explore new content types",
        "trigger": lambda s: s.get("diversity", s.get("content_diversity", 1)) < 0.3,
        "description": "You're watching very similar content. Explore new creators and topics.",
    },
    "increase_engagement": {
        "label": "Engage more deeply",
        "trigger": lambda s: s.get("depth", s.get("attention_score", 1)) < 0.3,
        "description": "You're scrolling quickly. Try watching reels fully before moving on.",
    },
    "maintain_balance": {
        "label": "Maintain current balance",
        "trigger": lambda s: True,  # always an eligible arm
        "description": "Your usage is balanced. Keep up the intentional consumption.",
    },
}


# ── State / reward ────────────────────────────────────────────────────────────

def compute_alignment(persona: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
    """Compute alignment between observed behaviour and healthy patterns (the state)."""
    traits = persona.get("traits", {})
    attention = traits.get("attention_score", 0)
    engagement = traits.get("engagement_score", 0)
    diversity = traits.get("content_diversity", 0)
    curiosity = traits.get("curiosity_score", 0)

    dimensions = {
        "intentionality": min(attention * 1.5, 1.0),
        "diversity": diversity,
        "depth": min(engagement + attention, 1.0) / 2,
        "wellbeing": 1.0 - min(features.get("total_events", 0) / 50, 1.0),
    }
    overall = sum(dimensions[d] * ALIGNMENT_DIMENSIONS[d]["weight"] for d in dimensions)

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


def context_key(alignment: Dict[str, Any]) -> str:
    """The contextual arm: the weakest alignment dimension defines the context."""
    dims = alignment.get("dimensions", {})
    if not dims:
        return "unknown"
    weakest = min(dims, key=dims.get)
    return f"weak_{weakest}"


# ── Policy store (Q-values) ───────────────────────────────────────────────────

async def _q_for_context(context: str) -> Dict[str, float]:
    rows = await fetch(
        "SELECT action_id, q_value FROM rl_policy WHERE context_key = $1", context
    )
    return {r["action_id"]: float(r["q_value"]) for r in rows}


async def update_q(context: str, action_id: str, reward: float) -> float:
    """Incremental-mean action-value update: Q += alpha * (reward - Q)."""
    row = await fetchrow(
        "SELECT q_value, n FROM rl_policy WHERE context_key = $1 AND action_id = $2",
        context, action_id,
    )
    q, n = (float(row["q_value"]), int(row["n"])) if row else (Q_INIT, 0)
    n1 = n + 1
    alpha = max(ALPHA_MIN, 1.0 / n1)
    new_q = q + alpha * (reward - q)
    await execute(
        """
        INSERT INTO rl_policy (context_key, action_id, q_value, n, updated_at)
        VALUES ($1, $2, $3, $4, NOW())
        ON CONFLICT (context_key, action_id)
        DO UPDATE SET q_value = EXCLUDED.q_value, n = EXCLUDED.n, updated_at = NOW()
        """,
        context, action_id, round(new_q, 4), n1,
    )
    logger.info("RL update ctx=%s action=%s reward=%.3f Q %.3f->%.3f (n=%d)",
                context, action_id, reward, q, new_q, n1)
    return new_q


async def learn_from_transition(user_id: str, current_score: float) -> Optional[Dict[str, Any]]:
    """Reward the previously-suggested action by the alignment change since then."""
    row = await fetchrow(
        "SELECT action_type, state FROM actions_log WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        user_id,
    )
    if not row:
        return None
    state = row["state"]
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except Exception:
            state = {}
    prev_align = (state or {}).get("alignment_before")
    ctx = (state or {}).get("context_key")
    if prev_align is None or ctx is None:
        return None
    # Improvement -> reward > 0.5; decline -> reward < 0.5; clipped to [0,1].
    reward = max(0.0, min(1.0, 0.5 + (current_score - float(prev_align))))
    new_q = await update_q(ctx, row["action_type"], reward)
    return {"action": row["action_type"], "context": ctx,
            "reward": round(reward, 3), "new_q": round(new_q, 4)}


# ── Policy (action selection) ─────────────────────────────────────────────────

async def suggest_action(alignment: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
    """Epsilon-greedy action selection over learned Q-values for the context."""
    merged = {**features, **alignment.get("dimensions", {})}
    applicable = [
        {"action_id": aid, "label": a["label"], "description": a["description"]}
        for aid, a in ACTIONS.items() if a["trigger"](merged)
    ]
    if not applicable:
        applicable = [{
            "action_id": "maintain_balance",
            "label": ACTIONS["maintain_balance"]["label"],
            "description": ACTIONS["maintain_balance"]["description"],
        }]

    ctx = context_key(alignment)
    qvals = await _q_for_context(ctx)

    if random.random() < EPSILON:
        chosen = random.choice(applicable)
        mode = "explore"
    else:
        chosen = max(applicable, key=lambda a: qvals.get(a["action_id"], Q_INIT))
        mode = "exploit"

    return {
        "action": chosen,
        "all_suggestions": applicable,
        "expected_reward": round(qvals.get(chosen["action_id"], Q_INIT), 3),
        "current_alignment": alignment.get("overall_score", 0),
        "context_key": ctx,
        "policy_mode": mode,
    }


# ── Logging / inspection ──────────────────────────────────────────────────────

async def log_action(
    user_id: str,
    action_type: str,
    action_data: Dict[str, Any],
    state: Dict[str, Any],
    reward: float,
) -> int:
    """Log an RL action + the state it was taken in (for the next reward step)."""
    row = await fetchrow(
        """
        INSERT INTO actions_log (user_id, action_type, action_data, state, reward)
        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)
        RETURNING id
        """,
        user_id, action_type, json.dumps(action_data), json.dumps(state), reward,
    )
    logger.info("Logged RL action id=%d user=%s reward=%.3f", row["id"], user_id, reward)
    return row["id"]


async def record_feedback(user_id: str, action_id: str, context: str, reward: float) -> Dict[str, Any]:
    """Explicit external reward signal (e.g. user rating a suggestion)."""
    reward = max(0.0, min(1.0, float(reward)))
    new_q = await update_q(context, action_id, reward)
    return {"context": context, "action": action_id, "reward": round(reward, 3), "new_q": round(new_q, 4)}


async def get_policy() -> List[Dict[str, Any]]:
    """Return the learned Q-table for inspection / dashboard."""
    rows = await fetch(
        "SELECT context_key, action_id, q_value, n, updated_at FROM rl_policy "
        "ORDER BY context_key, q_value DESC"
    )
    return [{
        "context_key": r["context_key"], "action_id": r["action_id"],
        "q_value": round(float(r["q_value"]), 4), "n": int(r["n"]),
        "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
    } for r in rows]


async def get_action_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    rows = await fetch(
        """
        SELECT id, action_type, action_data, state, reward, created_at
        FROM actions_log WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2
        """,
        user_id, limit,
    )
    return [{
        "id": r["id"], "action_type": r["action_type"],
        "action_data": r["action_data"], "state": r["state"],
        "reward": float(r["reward"]), "created_at": r["created_at"].isoformat(),
    } for r in rows]
