"""
RL API — inspect and drive the contextual-bandit policy.

  GET  /rl/policy            -> learned Q-table (context, action, Q, samples)
  GET  /rl/history           -> recent actions + rewards for a user
  POST /rl/feedback          -> explicit reward for a (context, action)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.services import rl_layer

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    context_key: str
    action_id: str
    reward: float  # 0..1  (1 = the suggestion helped, 0 = it did not)


@router.get("/rl/policy", response_model=list)
async def get_rl_policy():
    """The learned action-value table (contextual bandit)."""
    return await rl_layer.get_policy()


@router.get("/rl/history", response_model=list)
async def get_rl_history(
    user_id: str = Query(default="default"),
    limit: int = Query(default=20, le=100),
):
    """Recent RL actions and their rewards for a user."""
    return await rl_layer.get_action_history(user_id, limit)


@router.post("/rl/feedback")
async def post_rl_feedback(req: FeedbackRequest):
    """Apply an explicit reward to the policy (online learning update)."""
    if req.action_id not in rl_layer.ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action_id: {req.action_id}")
    result = await rl_layer.record_feedback(
        user_id="", action_id=req.action_id, context=req.context_key, reward=req.reward,
    )
    return {"success": True, **result}
