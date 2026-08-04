"""
Insights API — the exportable "Algorithmic Identity Profile" product surface
for ad agencies / audience research, mental-health & wellbeing research, and
academic behavioral research. See app/services/insights_export.py.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.api.deps import enforce_write_match, resolve_user_id
from app.services import insights_export, campaign_resonance

logger = logging.getLogger(__name__)
router = APIRouter()


class CampaignRequest(BaseModel):
    user_id: str = "default"
    campaign_text: str


@router.get("/insights/profile")
async def get_algorithmic_identity_profile(user_id: str = Depends(resolve_user_id)):
    """The full structured export — identity, interests, creator affinity,
    cognitive signals, audience segment, wellbeing signal."""
    return await insights_export.build_algorithmic_identity_profile(user_id)


@router.get("/insights/export.csv")
async def export_csv(
    user_id: str = Depends(resolve_user_id),
    table: str = Query(default="behavior_objects"),
):
    try:
        csv_text = await insights_export.export_table_csv(user_id, table)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{user_id}_{table}.csv"'},
    )


@router.post("/insights/campaign-resonance")
async def post_campaign_resonance(req: CampaignRequest, authorization: Optional[str] = Header(default=None)):
    """Score a hypothetical campaign/product description against this user's
    real algorithmic identity — the pre-outreach fit check an ad agency or
    creator-partnerships team would actually want."""
    enforce_write_match(authorization, req.user_id)
    if not req.campaign_text.strip():
        raise HTTPException(status_code=400, detail="campaign_text is required")
    result = await campaign_resonance.score_campaign(req.user_id, req.campaign_text)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
