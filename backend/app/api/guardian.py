"""
Guardian API — wellbeing monitoring, content alerts, and recommendations
derived from real behavior/event data. See app/services/wellbeing.py for the
underlying computation.
"""
import logging
from fastapi import APIRouter, Query

from app.services import wellbeing

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/guardian/report")
async def get_guardian_report(user_id: str = Query(default="default")):
    """Full wellbeing report: risk score, content alerts, positive
    highlights, session timing patterns, and recommendations."""
    return await wellbeing.compute_wellbeing_report(user_id)


@router.get("/guardian/sessions")
async def get_guardian_sessions(user_id: str = Query(default="default")):
    return await wellbeing.get_session_patterns(user_id)


@router.get("/guardian/alerts")
async def get_guardian_alerts(user_id: str = Query(default="default")):
    return await wellbeing.get_content_alerts(user_id)
