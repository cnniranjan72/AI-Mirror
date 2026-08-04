"""
Guardian API — wellbeing monitoring, content alerts, and recommendations
derived from real behavior/event data. See app/services/wellbeing.py for the
underlying computation.
"""
import logging
from fastapi import APIRouter, Depends, Query

from app.api.deps import resolve_user_id
from app.services import wellbeing

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/guardian/report")
async def get_guardian_report(user_id: str = Depends(resolve_user_id)):
    """Full wellbeing report: risk score, content alerts, positive
    highlights, session timing patterns, and recommendations."""
    return await wellbeing.compute_wellbeing_report(user_id)


@router.get("/guardian/sessions")
async def get_guardian_sessions(user_id: str = Depends(resolve_user_id)):
    return await wellbeing.get_session_patterns(user_id)


@router.get("/guardian/alerts")
async def get_guardian_alerts(user_id: str = Depends(resolve_user_id)):
    return await wellbeing.get_content_alerts(user_id)


@router.get("/guardian/alert-log")
async def get_guardian_alert_log(user_id: str = Depends(resolve_user_id), limit: int = Query(default=20)):
    """Persistent risk-level alert history — the in-app push-equivalent.
    A new row is only written when risk_level actually changes (see
    wellbeing._maybe_log_alert), so this is a real state-change log, not
    a per-page-view snapshot."""
    return await wellbeing.get_alert_log(user_id, limit)


@router.get("/guardian/alert-log/unacknowledged-count")
async def get_guardian_unacknowledged_count(user_id: str = Depends(resolve_user_id)):
    return {"count": await wellbeing.get_unacknowledged_alert_count(user_id)}


@router.post("/guardian/alert-log/{alert_id}/acknowledge")
async def acknowledge_guardian_alert(alert_id: str, user_id: str = Depends(resolve_user_id)):
    await wellbeing.acknowledge_alert(user_id, alert_id)
    return {"success": True}
