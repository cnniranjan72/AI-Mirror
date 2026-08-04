"""
Goals — the `goals` table has existed in the schema since V3 but nothing in
the codebase ever wrote to it (confirmed by grep: zero INSERT statements
anywhere, zero rows in production). This is the first real implementation:
create a goal, and get back an alignment score computed from the user's
actual behavior_objects — not a placeholder number.

Alignment is deterministic, same convention as evidence_engine.py/
campaign_resonance.py: real facts (importance_score, lifecycle_state) run
through explainable arithmetic, no LLM.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.postgres import fetch, fetchrow, execute

logger = logging.getLogger(__name__)
router = APIRouter()

GROWING_STATES = {"growing", "emerging"}
DECLINING_STATES = {"declining", "dormant", "archived"}


def _parse_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _matches(behavior_object: dict, keywords: List[str]) -> bool:
    haystack = [(behavior_object.get("topic") or "").lower()]
    haystack += [k.lower() for k in (_parse_json(behavior_object.get("keywords")) or [])]
    kw_lower = [k.lower() for k in keywords]
    return any(kw in h or h in kw for h in haystack for kw in kw_lower)


def _compute_alignment(goal_type: str, matching: List[dict]):
    if not matching:
        return 0.0, [], "No behavior yet matches this goal's keywords — alignment will update as you browse."

    avg_importance = sum(m["importance_score"] or 0 for m in matching) / len(matching)
    growing = sum(1 for m in matching if m["lifecycle_state"] in GROWING_STATES)
    declining = sum(1 for m in matching if m["lifecycle_state"] in DECLINING_STATES)
    trend_ratio = growing / max(1, growing + declining)

    if goal_type == "decrease":
        score = 0.5 * (1 - avg_importance) + 0.5 * (1 - trend_ratio)
        direction = "declining" if trend_ratio < 0.5 else "still growing"
        explanation = f"Matched topics are {direction}, averaging {round(avg_importance * 100)}% importance in your identity."
    elif goal_type == "maintain":
        score = avg_importance
        explanation = f"Matched topics average {round(avg_importance * 100)}% importance — {'holding steady' if score > 0.3 else 'fading, may need attention'}."
    else:  # increase
        score = 0.5 * avg_importance + 0.5 * trend_ratio
        direction = "growing" if trend_ratio >= 0.5 else "not yet trending up"
        explanation = f"Matched topics are {direction}, averaging {round(avg_importance * 100)}% importance in your identity."

    supporting = [
        {"topic": m["topic"], "lifecycle_state": m["lifecycle_state"], "importance_score": round(m["importance_score"] or 0, 3)}
        for m in sorted(matching, key=lambda m: -(m["importance_score"] or 0))[:5]
    ]
    return round(min(1.0, max(0.0, score)), 3), supporting, explanation


async def _score_goal(user_id: str, goal_type: str, keywords: List[str]):
    rows = await fetch(
        "SELECT topic, keywords, importance_score, lifecycle_state FROM behavior_objects WHERE user_id = $1",
        user_id,
    )
    objs = [dict(r) for r in rows]
    matching = [o for o in objs if _matches(o, keywords)]
    return _compute_alignment(goal_type, matching)


class GoalCreate(BaseModel):
    user_id: str = "default"
    goal_description: str
    goal_type: str = Field(default="increase", description="increase | decrease | maintain")
    target_keywords: List[str] = Field(default_factory=list, description="Topics/keywords this goal tracks against real behavior")
    target_date: Optional[str] = None


class GoalUpdate(BaseModel):
    status: Optional[str] = None  # active | completed | abandoned | paused
    goal_description: Optional[str] = None


@router.post("/goals")
async def create_goal(body: GoalCreate):
    if body.goal_type not in ("increase", "decrease", "maintain"):
        raise HTTPException(status_code=400, detail="goal_type must be increase, decrease, or maintain")
    if not body.target_keywords:
        raise HTTPException(status_code=400, detail="target_keywords is required — a goal needs something real to measure against")

    goal_id = f"goal_{uuid.uuid4().hex[:12]}"
    alignment_score, supporting, _ = await _score_goal(body.user_id, body.goal_type, body.target_keywords)

    target_date = None
    if body.target_date:
        try:
            target_date = datetime.fromisoformat(body.target_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="target_date must be ISO format")

    await execute(
        """
        INSERT INTO goals (goal_id, user_id, goal_description, goal_type, status,
                            progress, alignment_score, supporting_behaviors,
                            conflicting_behaviors, milestones, related_event_ids,
                            target_date, metadata)
        VALUES ($1, $2, $3, $4, 'active', $5, $5, $6::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, $7, $8::jsonb)
        """,
        goal_id, body.user_id, body.goal_description, body.goal_type,
        alignment_score, json.dumps(supporting), target_date,
        json.dumps({"target_keywords": body.target_keywords}),
    )
    return {"goal_id": goal_id, "alignment_score": alignment_score, "supporting_behaviors": supporting}


@router.get("/goals")
async def list_goals(user_id: str = Query(default="default"), status: Optional[str] = Query(default=None)):
    conditions = ["user_id = $1"]
    params = [user_id]
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")

    rows = await fetch(
        f"SELECT * FROM goals WHERE {' AND '.join(conditions)} ORDER BY created_at DESC",
        *params,
    )
    goals = []
    for r in rows:
        g = dict(r)
        metadata = _parse_json(g.get("metadata")) or {}
        keywords = metadata.get("target_keywords", [])
        # Re-score live on every read — alignment reflects the CURRENT identity,
        # not whatever it was when the goal was created.
        alignment_score, supporting, explanation = await _score_goal(user_id, g["goal_type"], keywords)
        if alignment_score != g["alignment_score"]:
            await execute(
                "UPDATE goals SET alignment_score = $1, progress = $1, supporting_behaviors = $2::jsonb, last_updated = NOW() WHERE goal_id = $3",
                alignment_score, json.dumps(supporting), g["goal_id"],
            )
        goals.append({
            "goal_id": g["goal_id"],
            "goal_description": g["goal_description"],
            "goal_type": g["goal_type"],
            "status": g["status"],
            "target_keywords": keywords,
            "alignment_score": alignment_score,
            "explanation": explanation,
            "supporting_behaviors": supporting,
            "target_date": g["target_date"].isoformat() if g["target_date"] else None,
            "created_at": g["created_at"].isoformat() if g["created_at"] else None,
        })
    return {"goals": goals}


@router.patch("/goals/{goal_id}")
async def update_goal(goal_id: str, body: GoalUpdate):
    existing = await fetchrow("SELECT goal_id FROM goals WHERE goal_id = $1", goal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Goal not found")

    if body.status:
        if body.status not in ("active", "completed", "abandoned", "paused"):
            raise HTTPException(status_code=400, detail="Invalid status")
        completed_at_clause = ", completed_at = NOW()" if body.status == "completed" else ""
        await execute(
            f"UPDATE goals SET status = $1, last_updated = NOW(){completed_at_clause} WHERE goal_id = $2",
            body.status, goal_id,
        )
    if body.goal_description:
        await execute(
            "UPDATE goals SET goal_description = $1, last_updated = NOW() WHERE goal_id = $2",
            body.goal_description, goal_id,
        )
    return {"success": True}


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str):
    result = await execute("DELETE FROM goals WHERE goal_id = $1", goal_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True}
