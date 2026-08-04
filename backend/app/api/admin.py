"""
Admin API — local debugging (GET /admin/errors) and the data-lifecycle
reprocess endpoint (POST /admin/reprocess, added alongside this file).
Not exposed in the dashboard UI this pass; curl-accessible for now.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import enforce_write_match
from app.db.postgres import execute, fetch

logger = logging.getLogger(__name__)
router = APIRouter()

# The full, confirmed write-set of V3Pipeline.run() (grep of INSERT INTO
# across pipeline/, reasoning/, identity/, engines/) — this is exactly what
# needs to be purged before a clean rebuild so re-clustering (which mints
# fresh behavior_object ids) doesn't leave orphaned evidence/inferences
# pointing at ids that no longer exist.
REPROCESS_TABLES = [
    "behavior_objects", "evidence", "inferences",
    "reflections", "self_models", "identity_snapshots", "identities",
]


@router.get("/admin/errors")
async def list_errors(
    limit: int = Query(default=50, le=200, ge=1),
    error_type: Optional[str] = Query(default=None),
):
    """Recent recorded errors — unhandled backend exceptions and (once wired)
    extension extraction failures. No auth: this is local-dev debugging
    tooling, not a per-user data endpoint."""
    conditions = []
    params: list = []
    if error_type:
        params.append(error_type)
        conditions.append(f"error_type = ${len(params)}")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows = await fetch(
        f"SELECT id, trace_id, user_id, path, method, error_type, message, "
        f"created_at::text FROM error_events {where} "
        f"ORDER BY created_at DESC LIMIT ${len(params)}",
        *params,
    )
    return {"errors": [dict(r) for r in rows]}


class ReprocessRequest(BaseModel):
    user_id: str
    confirm_user_id: str
    dry_run: bool = False


@router.post("/admin/reprocess")
async def reprocess_user(body: ReprocessRequest, authorization: Optional[str] = Header(default=None)):
    """Rebuild a user's behavior_objects/evidence/inferences/identity from
    their real, already-ingested events — replaces the one-off script this
    was hand-rolled as earlier: same purge-then-replay approach, but as a
    reusable, idempotent, auth-checked endpoint. Destructive and expensive,
    so unlike read endpoints there's no public-id exception — a token is
    always required, even for demo user_ids."""
    from backend.shared.contracts import BehaviorEvent, ContentType, EventSource
    from pipeline.orchestrator import V3Pipeline

    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required for reprocessing")
    enforce_write_match(authorization, body.user_id)
    if body.confirm_user_id != body.user_id:
        raise HTTPException(status_code=400, detail="confirm_user_id does not match user_id")

    rows = await fetch(
        "SELECT id, reel_id, username, caption, hashtags, audio, watch_time, "
        "timestamp, session_id, liked, saved, shared, commented, platform "
        "FROM events WHERE user_id = $1 ORDER BY timestamp ASC",
        body.user_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No events found for this user_id")

    if body.dry_run:
        current_counts = {}
        for table in REPROCESS_TABLES:
            row = await fetch(f"SELECT COUNT(*) AS c FROM {table} WHERE user_id = $1", body.user_id)
            current_counts[table] = row[0]["c"]
        return {
            "user_id": body.user_id,
            "dry_run": True,
            "events_loaded": len(rows),
            "current_counts": current_counts,
        }

    events = []
    for r in rows:
        hashtags = r["hashtags"]
        if isinstance(hashtags, str):
            hashtags = json.loads(hashtags)
        events.append(BehaviorEvent(
            event_id=str(r["id"]),
            source=EventSource.CHROME_EXTENSION,
            timestamp=r["timestamp"],
            session_id=r["session_id"] or f"session_{r['id']}",
            content_id=r["reel_id"],
            content_type=ContentType.REEL,
            creator=r["username"],
            caption=r["caption"] or "",
            hashtags=hashtags or [],
            audio_info=r["audio"] or "",
            watch_time=r["watch_time"] or 0,
            liked=bool(r["liked"]),
            saved=bool(r["saved"]),
            shared=bool(r["shared"]),
            commented=bool(r["commented"]),
            platform=r["platform"] or "instagram",
        ))

    deleted = {}
    for table in REPROCESS_TABLES:
        result = await execute(f"DELETE FROM {table} WHERE user_id = $1", body.user_id)
        # asyncpg execute() returns a status string like "DELETE 12".
        deleted[table] = int(result.split()[-1]) if result.split()[-1].isdigit() else 0

    result = await V3Pipeline().run(body.user_id, events)
    if result.errors:
        raise HTTPException(status_code=500, detail=f"Pipeline errors during reprocess: {result.errors}")

    return {
        "user_id": body.user_id,
        "dry_run": False,
        "events_loaded": len(events),
        "deleted": deleted,
        "pipeline_result": {
            "behavior_object_count": len(result.behavior_objects),
            "evidence_count": len(result.evidence),
            "inference_count": len(result.inferences),
            "reflection_count": 1 if result.reflection else 0,
            "identity_version": result.identity.identity_version if result.identity else None,
        },
    }
