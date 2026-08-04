"""
GET /timeline — unified chronological behavioral history across Instagram and
YouTube, with real (not fabricated) identity/evidence/memory linkage.

Every row is a raw `events` row (an actual watch/like/save action). For each
one we reverse-index the small per-user tables that reference it by event id
(`behavior_objects.supporting_event_ids`, `evidence.supporting_events`,
`memories.source_event_ids`) so a card can honestly show "this event
contributed to your AI Research behavior object at 0.82 confidence" instead
of a guessed annotation. `attention` is derived directly from watch_time —
no invented signal.
"""
import json
import logging
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Query

from app.db.postgres import fetch

logger = logging.getLogger(__name__)
router = APIRouter()

SKIPPED_MAX_SECONDS = 3
DEEP_MIN_SECONDS = 30


def _parse_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _attention_for(watch_time: float) -> str:
    wt = watch_time or 0
    if wt < SKIPPED_MAX_SECONDS:
        return "skipped"
    if wt >= DEEP_MIN_SECONDS:
        return "deep"
    return "shallow"


def _impact_for(scores: list) -> str:
    if not scores:
        return "none"
    top = max(scores)
    if top >= 0.7:
        return "high"
    if top >= 0.4:
        return "medium"
    return "low"


@router.get("/timeline")
async def get_timeline(
    user_id: str = Query(default="default"),
    platform: Optional[str] = Query(default=None, description="instagram | youtube"),
    liked_only: bool = Query(default=False),
    saved_only: bool = Query(default=False),
    attention: Optional[str] = Query(default=None, description="deep | shallow | skipped"),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=30, le=100, ge=1),
    before_id: Optional[int] = Query(default=None, description="cursor: return events older than this id"),
):
    conditions = ["user_id = $1"]
    params: list = [user_id]

    if platform:
        params.append(platform)
        conditions.append(f"platform = ${len(params)}")
    if liked_only:
        conditions.append("liked = TRUE")
    if saved_only:
        conditions.append("saved = TRUE")
    if search:
        params.append(f"%{search}%")
        conditions.append(f"(caption ILIKE ${len(params)} OR username ILIKE ${len(params)})")
    if before_id:
        params.append(before_id)
        conditions.append(f"id < ${len(params)}")

    params.append(limit)
    query = f"""
        SELECT id, platform, surface, username, caption, hashtags, watch_time, timestamp,
               liked, saved, shared, commented, following, like_count, comment_count, repost_count
        FROM events
        WHERE {' AND '.join(conditions)}
        ORDER BY id DESC
        LIMIT ${len(params)}
    """
    events = [dict(r) for r in await fetch(query, *params)]
    if attention:
        events = [e for e in events if _attention_for(e["watch_time"]) == attention]
    if not events:
        return {"events": [], "next_before_id": None}

    event_ids = {e["id"] for e in events}

    bos = await fetch(
        "SELECT topic, confidence_score, importance_score, supporting_event_ids "
        "FROM behavior_objects WHERE user_id = $1",
        user_id,
    )
    evs = await fetch(
        "SELECT evidence_type, explanation, confidence, supporting_events "
        "FROM evidence WHERE user_id = $1",
        user_id,
    )
    mems = await fetch(
        "SELECT memory_type, content, importance_score, source_event_ids "
        "FROM memories WHERE user_id = $1",
        user_id,
    )

    bo_index = defaultdict(list)
    for row in bos:
        for eid in _parse_json(row["supporting_event_ids"]) or []:
            try:
                eid = int(eid)
            except (TypeError, ValueError):
                continue
            if eid in event_ids:
                bo_index[eid].append({
                    "topic": row["topic"],
                    "confidence_score": row["confidence_score"],
                    "importance_score": row["importance_score"],
                })

    ev_index = defaultdict(list)
    for row in evs:
        for eid in _parse_json(row["supporting_events"]) or []:
            try:
                eid = int(eid)
            except (TypeError, ValueError):
                continue
            if eid in event_ids:
                ev_index[eid].append({
                    "evidence_type": row["evidence_type"],
                    "explanation": row["explanation"],
                    "confidence": row["confidence"],
                })

    mem_index = defaultdict(list)
    for row in mems:
        for eid in _parse_json(row["source_event_ids"]) or []:
            try:
                eid = int(eid)
            except (TypeError, ValueError):
                continue
            if eid in event_ids:
                mem_index[eid].append({
                    "memory_type": row["memory_type"],
                    "content": row["content"],
                    "importance_score": row["importance_score"],
                })

    results = []
    for e in events:
        eid = e["id"]
        behavior_objects = bo_index.get(eid, [])
        evidence = ev_index.get(eid, [])
        results.append({
            **e,
            "hashtags": _parse_json(e["hashtags"]) or [],
            "timestamp": e["timestamp"].isoformat() if e["timestamp"] else None,
            "attention": _attention_for(e["watch_time"]),
            "impact": _impact_for(
                [b["importance_score"] for b in behavior_objects] +
                [x["confidence"] for x in evidence]
            ),
            "behavior_objects": behavior_objects,
            "evidence": evidence,
            "memories": mem_index.get(eid, []),
        })

    return {
        "events": results,
        "next_before_id": events[-1]["id"] if len(events) == limit else None,
    }
