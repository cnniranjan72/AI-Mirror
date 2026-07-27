"""
Guardian / Wellbeing analysis — deterministic, data-derived signal about HOW
a person's platform usage is affecting them: session timing, content
sensitivity exposure, engagement depth ("scanning" vs "attentive"), and
creator/topic dependence. Every number here traces back to real events and
behavior objects already in the database — nothing is a canned score.

This is intentionally rule-based, not ML-based: every flag must be
explainable ("why is this flagged?") to be usable by a guardian, a clinician,
or a researcher. See ALIGNMENT_DIMENSIONS in rl_layer.py for the related (but
distinct) behavioral-alignment framing used by the RL loop.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.db.postgres import fetch, fetchrow, execute

logger = logging.getLogger(__name__)

# Content-sensitivity categories. Applied to topic/keyword/subtopic text
# already extracted by the pipeline — this flags CONTENT SIGNAL a guardian or
# clinician may want visibility into, not a diagnosis of the user.
SENSITIVE_CATEGORIES: Dict[str, List[str]] = {
    "mental_health": ["mentalhealth", "anxiety", "depression", "stress", "therapy",
                       "selfharm", "suicide", "burnout", "trauma"],
    "body_image": ["bodyimage", "diet", "weightloss", "thinspo", "bodygoals"],
    "substance": ["alcohol", "drugs", "vape", "vaping", "smoking", "weed"],
    "violence": ["violence", "fight", "gore", "war", "shooting"],
    "financial_risk": ["crypto", "gambling", "bet", "betting", "forex", "trading"],
}

NIGHT_HOURS = set(range(23, 24)) | set(range(0, 5))  # 11pm-5am local-naive


async def get_session_patterns(user_id: str) -> Dict[str, Any]:
    """Timing-based usage signal: late-night share, longest streak, cadence."""
    rows = await fetch(
        "SELECT timestamp, watch_time FROM events WHERE user_id = $1 "
        "ORDER BY timestamp DESC LIMIT 2000",
        user_id,
    )
    if not rows:
        return {
            "total_events": 0, "total_watch_time_sec": 0, "late_night_share": 0.0,
            "late_night_events": 0, "avg_watch_time_sec": 0, "hourly_distribution": {},
        }

    hourly = {h: 0 for h in range(24)}
    night_count = 0
    total_watch = 0.0
    for r in rows:
        ts = r["timestamp"]
        if ts is None:
            continue
        hourly[ts.hour] = hourly.get(ts.hour, 0) + 1
        if ts.hour in NIGHT_HOURS:
            night_count += 1
        total_watch += float(r["watch_time"] or 0)

    n = len(rows)
    return {
        "total_events": n,
        "total_watch_time_sec": round(total_watch, 1),
        "avg_watch_time_sec": round(total_watch / n, 1) if n else 0,
        "late_night_events": night_count,
        "late_night_share": round(night_count / n, 3) if n else 0.0,
        "hourly_distribution": hourly,
    }


def _matching_sensitive_categories(text: str) -> List[str]:
    hay = text.lower()
    return [cat for cat, kws in SENSITIVE_CATEGORIES.items() if any(k in hay for k in kws)]


async def get_content_alerts(user_id: str) -> List[Dict[str, Any]]:
    """Behavior objects whose topic/keywords/subtopics match a sensitive
    content category. Each alert cites the exact matching object as evidence."""
    rows = await fetch(
        "SELECT topic, keywords, subtopics, confidence_score, temporal_statistics, updated_at "
        "FROM behavior_objects WHERE user_id = $1",
        user_id,
    )
    import json
    alerts = []
    for r in rows:
        kw = r["keywords"]
        st = r["subtopics"]
        if isinstance(kw, str):
            try: kw = json.loads(kw)
            except Exception: kw = []
        if isinstance(st, str):
            try: st = json.loads(st)
            except Exception: st = []
        text = " ".join([r["topic"] or ""] + (kw or []) + (st or []))
        cats = _matching_sensitive_categories(text)
        if not cats:
            continue
        ts = r["temporal_statistics"]
        if isinstance(ts, str):
            try: ts = json.loads(ts)
            except Exception: ts = {}
        alerts.append({
            "topic": r["topic"],
            "categories": cats,
            "occurrence_count": (ts or {}).get("occurrence_count", 0),
            "confidence": float(r["confidence_score"] or 0),
            "last_seen": r["updated_at"].isoformat() if r["updated_at"] else None,
        })
    alerts.sort(key=lambda a: a["occurrence_count"], reverse=True)
    return alerts


async def get_positive_highlights(user_id: str) -> List[Dict[str, Any]]:
    """The healthy inverse of alerts: growing, high-completion educational/
    skill-building engagement — genuinely worth surfacing as a positive."""
    rows = await fetch(
        "SELECT topic, lifecycle_state, confidence_score, watch_statistics, keywords "
        "FROM behavior_objects WHERE user_id = $1 AND lifecycle_state IN ('growing','stable','mature')",
        user_id,
    )
    import json
    edu_keywords = ["learn", "tutorial", "education", "course", "study", "skill",
                     "how to", "guide", "programming", "coding", "science"]
    highlights = []
    for r in rows:
        kw = r["keywords"]
        if isinstance(kw, str):
            try: kw = json.loads(kw)
            except Exception: kw = []
        text = (r["topic"] or "") + " " + " ".join(kw or [])
        if not any(k in text.lower() for k in edu_keywords):
            continue
        ws = r["watch_statistics"]
        if isinstance(ws, str):
            try: ws = json.loads(ws)
            except Exception: ws = {}
        completion = (ws or {}).get("completion_rate", 0)
        highlights.append({
            "topic": r["topic"], "lifecycle_state": r["lifecycle_state"],
            "completion_rate": completion, "confidence": float(r["confidence_score"] or 0),
        })
    highlights.sort(key=lambda h: h["completion_rate"], reverse=True)
    return highlights


async def compute_wellbeing_report(user_id: str) -> Dict[str, Any]:
    """The full Guardian report: session patterns, alerts, highlights, a
    composite risk score, and deterministic recommendations."""
    sessions = await get_session_patterns(user_id)
    alerts = await get_content_alerts(user_id)
    highlights = await get_positive_highlights(user_id)

    # Creator/topic dependence and engagement-depth are already computed by
    # the reasoning rule engine as inferences — reuse them rather than
    # recomputing, so the Guardian view and the Memory view never disagree.
    inf_rows = await fetch(
        "SELECT rule_name, label, description, confidence FROM inferences WHERE user_id = $1",
        user_id,
    )
    scanning = next((r for r in inf_rows if r["rule_name"] == "EngagementDepthRule"
                     and "scanning" in (r["description"] or "").lower()), None)
    dependence = next((r for r in inf_rows if r["rule_name"] == "CreatorDependenceRule"), None)
    entertainment = next((r for r in inf_rows if r["rule_name"] == "EntertainmentDominanceRule"), None)

    # Composite risk: each real, independently-computed signal contributes a
    # bounded amount. This is intentionally simple/explainable — a guardian or
    # clinician can trace every point back to a concrete behavior.
    risk = 0.0
    risk_factors = []
    if sessions["late_night_share"] > 0.25:
        risk += min(0.3, sessions["late_night_share"])
        risk_factors.append(f"{sessions['late_night_share']:.0%} of activity is late-night (11pm-5am)")
    if alerts:
        risk += min(0.3, len(alerts) * 0.08)
        risk_factors.append(f"{len(alerts)} sensitive-content topic(s) detected")
    if scanning:
        risk += 0.2
        risk_factors.append("Engagement style trends toward quick/scanning rather than attentive")
    if dependence:
        risk += 0.1
        risk_factors.append("Heavy dependence on a small set of creators")
    if entertainment:
        risk += 0.1
        risk_factors.append("Entertainment content dominates over 60% of activity")
    risk = round(min(1.0, risk), 3)

    recommendations = []
    if sessions["late_night_share"] > 0.25:
        recommendations.append("Consider a wind-down reminder before late-night sessions.")
    if alerts:
        cats = sorted({c for a in alerts for c in a["categories"]})
        recommendations.append(f"Sensitive content categories present: {', '.join(cats)} — worth a check-in conversation.")
    if scanning:
        recommendations.append("Encourage longer-form, single-focus content to build attention span.")
    if dependence:
        recommendations.append("Suggest exploring new creators to reduce parasocial dependence.")
    if not recommendations:
        recommendations.append("No elevated risk factors detected — usage pattern looks balanced.")

    risk_level = "low" if risk < 0.3 else ("moderate" if risk < 0.6 else "elevated")
    await _maybe_log_alert(user_id, risk_level, risk, risk_factors)

    return {
        "user_id": user_id,
        "risk_score": risk,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "session_patterns": sessions,
        "content_alerts": alerts,
        "positive_highlights": highlights,
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat(),
    }


async def _maybe_log_alert(user_id: str, risk_level: str, risk_score: float, risk_factors: List[str]) -> None:
    """Record a persistent alert row when risk is elevated/moderate — the
    in-app equivalent of a push notification (no external delivery infra
    like email/webhooks is configured, so this is the honest version:
    a real, queryable alert history instead of a fresh computation that
    vanishes the moment the page closes). Deduped against the most recent
    alert for this user so it only grows on an actual state change, not
    once per page view."""
    if risk_level == "low":
        return
    try:
        last = await fetchrow(
            "SELECT risk_level FROM guardian_alerts WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
            user_id,
        )
        if last and last["risk_level"] == risk_level:
            return
        alert_id = f"alert_{user_id}_{int(datetime.utcnow().timestamp() * 1000)}"
        await execute(
            "INSERT INTO guardian_alerts (alert_id, user_id, risk_level, risk_score, risk_factors) "
            "VALUES ($1,$2,$3,$4,$5::jsonb) ON CONFLICT (alert_id) DO NOTHING",
            alert_id, user_id, risk_level, risk_score, json.dumps(risk_factors),
        )
    except Exception as e:
        logger.warning(f"Could not log guardian alert: {e}")


async def get_alert_log(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    rows = await fetch(
        "SELECT alert_id, risk_level, risk_score, risk_factors, acknowledged, created_at "
        "FROM guardian_alerts WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        user_id, limit,
    )
    out = []
    for r in rows:
        rf = r["risk_factors"]
        if isinstance(rf, str):
            try:
                rf = json.loads(rf)
            except Exception:
                rf = []
        out.append({
            "alert_id": r["alert_id"],
            "risk_level": r["risk_level"],
            "risk_score": float(r["risk_score"]),
            "risk_factors": rf or [],
            "acknowledged": r["acknowledged"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return out


async def get_unacknowledged_alert_count(user_id: str) -> int:
    row = await fetchrow(
        "SELECT COUNT(*) as c FROM guardian_alerts WHERE user_id = $1 AND acknowledged = FALSE",
        user_id,
    )
    return int(row["c"]) if row else 0


async def acknowledge_alert(user_id: str, alert_id: str) -> None:
    await execute(
        "UPDATE guardian_alerts SET acknowledged = TRUE WHERE user_id = $1 AND alert_id = $2",
        user_id, alert_id,
    )
