"""Rebuild behaviour objects for accounts whose ingest or seed was cut off.

Events are stored one statement at a time and the pipeline runs afterwards, in
the same request. If the request dies in between - a timeout, a dropped
connection, an instance recycling - the events are already committed and the
pipeline never runs. Nothing revisits stored events, so the account stays that
way forever: the dashboard shows a real event count, and every question asked
of it answers "No behavioral data found yet".

Measured on the deployed instance before this existed: of 15 demo accounts, 7
held events and no behaviour objects. Four of those had all 800 events stored,
so the inserts had finished and only consolidation was lost. Across all
accounts, 13 of 35 were in this state, including one with 159 events and one
with 109.

This is the repair. It finds accounts with events and nothing derived from
them, and runs the same pipeline over the events already in the database.

    python reprocess_stuck.py                 # report what would be rebuilt
    python reprocess_stuck.py --apply         # rebuild it
    python reprocess_stuck.py --user <id>     # just this one
    python reprocess_stuck.py --limit 5       # the first N

Nothing is destroyed. Behaviour objects are derived from events, and this
derives them again from events that are already stored; an account that
already has them is skipped rather than rebuilt, so running it twice is not
different from running it once.

The prevention is separate and lives in app/api/seed.py: the insert loop is now
a single statement, which removes the latency that made the timeout likely.
This script exists for the accounts that were already stranded, and for the
next time a request dies for some other reason.
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.db.postgres import close_pool, fetch, init_pool  # noqa: E402
from backend.core.behavior_gateway import get_behavior_gateway  # noqa: E402
from backend.shared.contracts import EventSource  # noqa: E402

# Below this there is nothing to consolidate: the engine needs three events
# sharing a topic or a creator before it will form anything, so an account with
# fewer than that is not stuck, it is new.
MIN_EVENTS_TO_BOTHER = 3


async def stuck_accounts(user: str = None):
    """Accounts holding events with no behaviour objects derived from them."""
    rows = await fetch(
        """
        SELECT e.user_id, COUNT(*) AS events
        FROM events e
        WHERE NOT EXISTS (
            SELECT 1 FROM behavior_objects b WHERE b.user_id = e.user_id)
          AND ($1::text IS NULL OR e.user_id = $1)
        GROUP BY e.user_id
        HAVING COUNT(*) >= $2
        ORDER BY COUNT(*) DESC
        """,
        user, MIN_EVENTS_TO_BOTHER,
    )
    return rows


async def _normalized_events(user_id: str):
    """The user's stored events, in the shape the pipeline expects.

    Read back from the events table rather than from a request body, because
    the request that carried them is long gone. event_id is set to the real row
    id for the same reason ingest does it: the Timeline page's reverse index
    walks supporting_event_ids back to specific rows.
    """
    raw = await fetch(
        "SELECT id, reel_id, username, caption, hashtags, audio, watch_time, "
        "timestamp, session_id, liked, saved, shared, commented, following, "
        "platform, surface FROM events WHERE user_id = $1 ORDER BY timestamp",
        user_id,
    )
    payload = {"events": []}
    for r in raw:
        hashtags = r["hashtags"]
        if isinstance(hashtags, str):
            try:
                hashtags = json.loads(hashtags)
            except (ValueError, TypeError):
                hashtags = []
        payload["events"].append({
            "reel_id": r["reel_id"],
            "username": r["username"],
            "caption": r["caption"],
            "hashtags": hashtags or [],
            "audio_info": r["audio"],
            "watch_time": r["watch_time"],
            "timestamp": r["timestamp"].isoformat(),
            "session_id": r["session_id"],
            "liked": r["liked"],
            "saved": r["saved"],
            "shared": r["shared"],
            "commented": r["commented"],
            "following": r["following"],
            "platform": r["platform"],
            "surface": r["surface"],
            "source_url": "",
        })

    by_content = {r["reel_id"]: r["id"] for r in raw}
    gateway = get_behavior_gateway()
    normalized = gateway.process_batch(payload, EventSource.CHROME_EXTENSION)
    for bev in normalized:
        db_id = by_content.get(bev.content_id)
        if db_id is not None:
            bev.event_id = str(db_id)
    return normalized


async def rebuild(user_id: str):
    from pipeline.orchestrator import V3Pipeline

    normalized = await _normalized_events(user_id)
    if not normalized:
        return None
    pipeline = V3Pipeline()
    existing = await pipeline.load_identity(user_id)
    return await pipeline.run(
        user_id=user_id, events=normalized, existing_identity=existing)


async def main(apply: bool, user: str, limit: int) -> int:
    await init_pool()
    try:
        rows = await stuck_accounts(user)
        if limit:
            rows = rows[:limit]

        if not rows:
            print("No account is holding events with nothing derived from them.")
            return 0

        print("accounts with events and no behaviour objects: %d" % len(rows))
        for r in rows:
            print("   %-34s %d events" % (r["user_id"][:34], r["events"]))

        if not apply:
            print("\nDry run. Pass --apply to rebuild these.")
            return 0

        print()
        failures = 0
        for r in rows:
            uid = r["user_id"]
            try:
                result = await rebuild(uid)
            except Exception as e:
                failures += 1
                print("   %-34s FAILED: %s" % (uid[:34], str(e)[:80]))
                continue
            if result is None:
                print("   %-34s no usable events" % uid[:34])
                continue
            print("   %-34s %d behaviours, %d evidence, %d inferences, identity v%s" % (
                uid[:34],
                len(result.behavior_objects), len(result.evidence),
                len(result.inferences),
                result.identity.identity_version if result.identity else "?",
            ))

        print("\nRebuilt %d account(s), %d failed." % (len(rows) - failures, failures))
        return 1 if failures else 0
    finally:
        await close_pool()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="write the rebuild")
    p.add_argument("--user", help="only this user_id")
    p.add_argument("--limit", type=int, default=0, help="at most N accounts")
    a = p.parse_args()
    raise SystemExit(asyncio.run(main(a.apply, a.user, a.limit)))
