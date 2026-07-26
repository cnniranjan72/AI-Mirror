"""
Insights API — the exportable "Algorithmic Identity Profile" product surface
for ad agencies / audience research, mental-health & wellbeing research, and
academic behavioral research. See app/services/insights_export.py.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.services import insights_export

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/insights/profile")
async def get_algorithmic_identity_profile(user_id: str = Query(default="default")):
    """The full structured export — identity, interests, creator affinity,
    cognitive signals, audience segment, wellbeing signal."""
    return await insights_export.build_algorithmic_identity_profile(user_id)


@router.get("/insights/export.csv")
async def export_csv(
    user_id: str = Query(default="default"),
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
