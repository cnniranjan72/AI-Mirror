"""
GET /diary/story — a weekly or monthly "story" narrated from real, computed
stats over the events table, with a real comparison to the prior period.

Not an LLM call: this project's own convention (see evidence_engine.py) is
that the deterministic pipeline decides the facts and a template turns them
into prose — an LLM only re-verbalizes already-decided facts elsewhere in the
app. Reusing that pattern here avoids depending on the fragile embedding/LLM
path just to render a diary page, and keeps every sentence traceable to a
real number.

The existing `reflections` table looks like it should back this, but each
row is written once per /ingest call with period_start == period_end (a
snapshot, not a calendar window) — using it here would silently mislabel
per-batch snapshots as "this week", so this endpoint aggregates directly
from events/behavior_objects instead.
"""
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.db.postgres import fetch

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _period_bounds(period: str, offset: int, now: datetime):
    if period == "month":
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Step back `offset` months by walking to day 1 repeatedly.
        start = first_of_this_month
        for _ in range(offset):
            start = (start - timedelta(days=1)).replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        prev_start = (start - timedelta(days=1)).replace(day=1)
        label = start.strftime("%B %Y")
        return start, end, prev_start, start, label
    # week: Monday-start ISO week
    start_of_this_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start = start_of_this_week - timedelta(weeks=offset)
    end = start + timedelta(weeks=1)
    prev_start = start - timedelta(weeks=1)
    label = f"Week of {start.strftime('%b %d, %Y')}"
    return start, end, prev_start, start, label


def _attention_bucket(watch_time: float) -> str:
    wt = watch_time or 0
    if wt < 3:
        return "skipped"
    if wt >= 30:
        return "deep"
    return "shallow"


async def _period_stats(user_id: str, start: datetime, end: datetime):
    events = await fetch(
        "SELECT id, platform, username, caption, hashtags, watch_time, liked, saved "
        "FROM events WHERE user_id = $1 AND timestamp >= $2 AND timestamp < $3",
        user_id, start, end,
    )
    events = [dict(r) for r in events]
    count = len(events)
    if count == 0:
        return {
            "event_count": 0, "platform_breakdown": {}, "liked_count": 0, "saved_count": 0,
            "deep_pct": 0, "shallow_pct": 0, "skipped_pct": 0, "avg_watch_time": 0,
            "top_topics": [], "top_creators": [],
        }

    platform_breakdown = Counter(e["platform"] for e in events)
    liked_count = sum(1 for e in events if e["liked"])
    saved_count = sum(1 for e in events if e["saved"])
    attention = Counter(_attention_bucket(e["watch_time"]) for e in events)
    avg_watch_time = sum(e["watch_time"] or 0 for e in events) / count
    top_creators = Counter(e["username"] for e in events if e["username"]).most_common(3)

    event_ids = {e["id"] for e in events}
    bos = await fetch(
        "SELECT topic, importance_score, supporting_event_ids FROM behavior_objects WHERE user_id = $1",
        user_id,
    )
    topic_hits = defaultdict(int)
    topic_importance = {}
    for row in bos:
        ids = _parse_json(row["supporting_event_ids"]) or []
        hits = 0
        for eid in ids:
            try:
                if int(eid) in event_ids:
                    hits += 1
            except (TypeError, ValueError):
                continue
        if hits:
            topic_hits[row["topic"]] += hits
            topic_importance[row["topic"]] = max(topic_importance.get(row["topic"], 0), row["importance_score"] or 0)

    top_topics = sorted(topic_hits.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return {
        "event_count": count,
        "platform_breakdown": dict(platform_breakdown),
        "liked_count": liked_count,
        "saved_count": saved_count,
        "deep_pct": round(100 * attention["deep"] / count),
        "shallow_pct": round(100 * attention["shallow"] / count),
        "skipped_pct": round(100 * attention["skipped"] / count),
        "avg_watch_time": round(avg_watch_time, 1),
        "top_topics": [{"topic": t, "events": n, "importance": round(topic_importance.get(t, 0), 3)} for t, n in top_topics],
        "top_creators": [{"username": u, "events": n} for u, n in top_creators],
    }


def _pct_delta(curr: int, prev: int) -> Optional[int]:
    if prev == 0:
        return None
    return round(100 * (curr - prev) / prev)


def _narrate(period_label: str, curr: dict, prev: dict) -> list:
    lines = []
    if curr["event_count"] == 0:
        return [f"No activity recorded for {period_label.lower()}."]

    lines.append(f"You engaged with {curr['event_count']} piece{'s' if curr['event_count'] != 1 else ''} of content this period.")

    platforms = curr["platform_breakdown"]
    if len(platforms) > 1:
        parts = [f"{v} on {k.capitalize()}" for k, v in sorted(platforms.items(), key=lambda kv: -kv[1])]
        lines.append(f"Split across platforms: {', '.join(parts)}.")
    elif platforms:
        lines.append(f"All of it was on {list(platforms.keys())[0].capitalize()}.")

    if curr["top_topics"]:
        top = curr["top_topics"][0]
        prev_top_events = next((t["events"] for t in prev.get("top_topics", []) if t["topic"] == top["topic"]), 0)
        delta = _pct_delta(top["events"], prev_top_events)
        delta_phrase = ""
        if delta is not None and delta != 0:
            direction = "more" if delta > 0 else "less"
            delta_phrase = f" - {abs(delta)}% {direction} than the period before"
        lines.append(f"\"{top['topic']}\" was your biggest focus, appearing in {top['events']} events{delta_phrase}.")

    event_delta = _pct_delta(curr["event_count"], prev["event_count"])
    if event_delta is not None and abs(event_delta) >= 10:
        direction = "more" if event_delta > 0 else "less"
        lines.append(f"That's {abs(event_delta)}% {direction} activity than the previous period.")

    if curr["deep_pct"] >= 40:
        lines.append(f"{curr['deep_pct']}% of your watching was deep attention - you were genuinely engaged, not just scrolling.")
    elif curr["skipped_pct"] >= 40:
        lines.append(f"{curr['skipped_pct']}% of what you saw was skipped in under 3 seconds - mostly passive scrolling this period.")

    if curr["liked_count"] or curr["saved_count"]:
        lines.append(f"You liked {curr['liked_count']} and saved {curr['saved_count']} piece{'s' if curr['saved_count'] != 1 else ''} of content.")

    return lines


@router.get("/diary/story")
async def get_diary_story(
    user_id: str = Query(default="default"),
    period: str = Query(default="week", description="week | month"),
    offset: int = Query(default=0, ge=0, le=52, description="0 = current period, 1 = previous, etc."),
):
    now = datetime.now(timezone.utc)
    start, end, prev_start, prev_end, label = _period_bounds(period, offset, now)

    curr_stats = await _period_stats(user_id, start, end)
    prev_stats = await _period_stats(user_id, prev_start, prev_end)

    return {
        "period": period,
        "offset": offset,
        "label": label,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "stats": curr_stats,
        "previous_stats": prev_stats,
        "story": _narrate(label, curr_stats, prev_stats),
        "has_more": curr_stats["event_count"] > 0 or offset == 0,
    }
