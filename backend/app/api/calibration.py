"""Accuracy ledger API — the user's verdict on what the system claimed.

  POST /calibration/verdict   -> record "that's right / wrong / not sure"
  GET  /calibration/report    -> accuracy and calibration, by confidence band
  GET  /calibration/open      -> claims still awaiting an answer

See app/services/calibration.py for why calibration rather than accuracy.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import enforce_write_match, resolve_user_id
from app.core.rate_limit import verdict_rate_limit
from app.services import calibration

logger = logging.getLogger(__name__)
router = APIRouter()


class VerdictRequest(BaseModel):
    user_id: str
    claim_type: str
    claim_id: str
    verdict: str


@router.post("/calibration/verdict", dependencies=[Depends(verdict_rate_limit)])
async def record_verdict(
    body: VerdictRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Record the user's verdict on one claim the system made about them.

    Unlike /rl/feedback this writes only to the caller's own ledger, never to
    anything shared, so it needs no signed-in gate beyond the usual write
    check, and it gets its own limiter rather than the feedback one — see
    VERDICT_LIMITER for why sharing it throttled legitimate use.
    """
    enforce_write_match(authorization, body.user_id)
    try:
        result = await calibration.record_verdict(
            user_id=body.user_id,
            claim_type=body.claim_type,
            claim_id=body.claim_id,
            verdict=body.verdict,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result.get("recorded"):
        # Also the not-yours case: record_verdict scopes its lookup by user_id.
        raise HTTPException(status_code=404, detail="Claim not found for this user")
    return result


@router.get("/calibration/report")
async def calibration_report(user_id: str = Depends(resolve_user_id)):
    """How often the system was right, broken down by how sure it claimed to be."""
    return await calibration.build_calibration_report(user_id)


@router.get("/calibration/open")
async def open_claims(
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=20, le=100),
):
    """Claims still awaiting a verdict, most confident first."""
    return await calibration.list_open_claims(user_id, limit)


@router.get("/calibration/answered")
async def answered_claims(
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=50, le=200),
):
    """Claims already answered, so a verdict can be changed.

    A correction the user cannot reverse is a trap rather than a control, and
    the Report tells them they can take it back — this is what makes that
    true. Each row carries live_claim_id, the id to POST against now; the
    stored claim_id is usually stale because the pipeline regenerates
    inferences on every ingest.
    """
    return await calibration.list_answered_claims(user_id, limit)
