"""
RL API — inspect and drive the contextual-bandit policy.

  GET  /rl/policy            -> learned Q-table (context, action, Q, samples)
  GET  /rl/history           -> recent actions + rewards for a user
  POST /rl/feedback          -> explicit reward for a (context, action)

A note on /rl/feedback, because it is not shaped like the rest of the API.

`rl_policy` is keyed on (context_key, action_id) with no user_id: it is ONE
table shared by every user of the service, and it decides which nudge each of
them is shown. Feedback is therefore not personal data being written to the
caller's own row — it is a write to everyone's model.

That endpoint used to take context_key and reward as free-form body fields
with no authentication and no rate limit, which made all three of these true
for anyone with curl:

  * The update rule is Q += max(0.05, 1/n) * (reward - Q). The 0.05 floor
    keeps late feedback influential on purpose, so repeated posts converge on
    whatever value the caller picks: ~60 requests move any established Q to
    within 5% of it, and 200 pin it exactly. A shared policy could be set to
    anything.
  * n is incremented by those same posts, and alpha shrinks as n grows, so
    fabricated feedback also permanently dilutes the weight of real feedback.
  * context_key was unvalidated, so every distinct string inserted a row into
    a shared table with no upper bound.

The fix keeps the signed-out demo working rather than putting the endpoint
behind a login. Anyone may still post, and the response is honest about what
happened: only an authenticated caller's feedback is applied to the shared
policy, and everyone else gets applied=false with a reason. Anonymous
feedback changes nothing, so there is nothing to poison.

/rl/policy stays public: it is aggregate model state, no user data in it.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Header
from pydantic import BaseModel, Field

from app.api.auth_api import _bearer
from app.api.deps import resolve_user_id
from app.core.rate_limit import feedback_rate_limit
from app.services import auth, rl_layer

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    context_key: str
    action_id: str
    # 0..1  (1 = the suggestion helped, 0 = it did not). Bounded here as well
    # as clamped downstream so a nonsense value is a 422, not a silent clamp.
    reward: float = Field(ge=0.0, le=1.0)


@router.get("/rl/policy", response_model=list)
async def get_rl_policy():
    """The learned action-value table (contextual bandit)."""
    return await rl_layer.get_policy()


@router.get("/rl/history", response_model=list)
async def get_rl_history(
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=20, le=100),
):
    """Recent RL actions and their rewards for a user."""
    return await rl_layer.get_action_history(user_id, limit)


@router.post("/rl/feedback", dependencies=[Depends(feedback_rate_limit)])
async def post_rl_feedback(
    req: FeedbackRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Apply an explicit reward to the shared policy (online learning update).

    Accepted from anyone so the signed-out demo still works; applied to the
    shared policy only for an authenticated caller. See the module docstring.
    """
    if req.action_id not in rl_layer.ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action_id: {req.action_id}")

    # A closed set, so the shared table cannot be grown by inventing contexts.
    if req.context_key not in rl_layer.VALID_CONTEXT_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown context_key: {req.context_key}",
        )

    token = _bearer(authorization)
    username = auth.verify_token(token) if token else None

    if not username:
        # Deliberately 200, not 401: the Learning page is browsable signed out
        # and clicking a rating should not look broken. The response says
        # plainly that nothing was learned.
        logger.info(
            "Unauthenticated RL feedback ignored (ctx=%s action=%s)",
            req.context_key, req.action_id,
        )
        return {
            "success": True,
            "applied": False,
            "reason": "Sign in to train the shared model. This policy is shared "
                      "by every user, so anonymous ratings are not applied.",
            "context": req.context_key,
            "action": req.action_id,
        }

    result = await rl_layer.record_feedback(
        user_id=username, action_id=req.action_id,
        context=req.context_key, reward=req.reward,
    )
    return {"success": True, "applied": True, **result}
