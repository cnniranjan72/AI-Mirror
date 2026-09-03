"""Read a user's stored events back as BehaviorEvents.

Consolidation needs to see a topic three times before it will believe in it.
For one request that is a reasonable bar; across requests it was being applied
to whatever happened to arrive together, and nothing else. The extension sends
batches of ten (chrome-extension/content.js BATCH_SIZE), so a creator whose
videos are spread over several batches never reached three in any one of them
and never became anything at all.

Measured on stored accounts, comparing topics that form in batches of ten
against topics that form when the same events are consolidated together:

    demo_ddz4smtf   800 events   25 of 31 topics form   19% never do
    demo_tx4m2pae   800 events   20 of 31 topics form   35% never do
    demo_vf35lyxj   159 events   15 of 26 topics form   50% never do

Almost all of the loss is creator clusters - "Content by <creator>" - which is
what one would expect: a creator needs three of their own videos inside a
ten-event window, while a topic can be carried by hashtags several creators
share.

So consolidation is given a window of the account's recent events rather than
only the ones in hand. Reading them back is one query; consolidating 800 of
them takes 15 ms, so the cost is the query, not the work.

Re-consolidating events already seen is safe by construction: the orchestrator
merges clusters into existing behaviour objects by topic and unions
supporting_event_ids, deriving occurrence_count from the deduplicated set. That
was done so a topic revisited over many ingests would accumulate; it also means
handing it the same event twice changes nothing.
"""
import json
import logging
from typing import List, Optional

from app.db.postgres import fetch
from backend.core.behavior_gateway import get_behavior_gateway
from backend.shared.contracts import BehaviorEvent, EventSource

logger = logging.getLogger(__name__)

# How far back consolidation looks. Chosen from what the window actually buys:
# on an 800-event account, 100 events yield 24 of 31 topics and 400 yield 30,
# so a few hundred captures nearly everything while keeping the read bounded
# for an account with years of history. An event that ages out has already had
# this many chances to find two siblings.
CONSOLIDATION_WINDOW = 500

_COLUMNS = (
    "id, reel_id, username, caption, hashtags, audio, watch_time, timestamp, "
    "session_id, liked, saved, shared, commented, following, platform, surface"
)


def _hashtags(value) -> list:
    """asyncpg hands jsonb back as text on some paths and a list on others.

    Getting this wrong costs every topic, silently: the events still normalize,
    they just carry no tags to group on.
    """
    if isinstance(value, str):
        try:
            return json.loads(value) or []
        except (ValueError, TypeError):
            return []
    return value or []


async def load_recent(user_id: str, limit: Optional[int] = CONSOLIDATION_WINDOW) -> List[BehaviorEvent]:
    """The account's most recent stored events, oldest first.

    event_id is set to the real events.id, as ingest does, because
    supporting_event_ids is what the Timeline page walks back to source rows. A
    BehaviorEvent carrying the normalizer's invented evt_xxxx would break that
    reverse index for anything consolidated from storage.
    """
    query = (
        "SELECT " + _COLUMNS + " FROM ("
        "  SELECT " + _COLUMNS + " FROM events WHERE user_id = $1"
        "  ORDER BY timestamp DESC" + (" LIMIT $2" if limit else "") +
        ") recent ORDER BY timestamp ASC"
    )
    args = (user_id, limit) if limit else (user_id,)
    try:
        rows = await fetch(query, *args)
    except Exception:
        logger.warning("Could not load stored events for %s", user_id, exc_info=True)
        return []

    if not rows:
        return []

    payload = {"events": [{
        "reel_id": r["reel_id"],
        "username": r["username"],
        "caption": r["caption"],
        "hashtags": _hashtags(r["hashtags"]),
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
    } for r in rows]}

    normalized = get_behavior_gateway().process_batch(
        payload, EventSource.CHROME_EXTENSION)

    by_content = {r["reel_id"]: r["id"] for r in rows}
    for bev in normalized:
        db_id = by_content.get(bev.content_id)
        if db_id is not None:
            bev.event_id = str(db_id)
    return normalized


def merge(stored: List[BehaviorEvent], incoming: List[BehaviorEvent]) -> List[BehaviorEvent]:
    """Everything to consolidate, without counting an event twice.

    Ingest stores events before running the pipeline, so the incoming batch is
    usually already inside the window and this is mostly deduplication. It is
    not merely defensive: a caller that has not stored yet must still have its
    events consolidated, and one that has must not have them doubled.

    Identity is (content id, timestamp), not event_id, because the two sources
    disagree about event_id - storage knows the row id, a freshly normalized
    batch may still carry the invented one. A genuine re-watch has a different
    timestamp and is correctly kept as a separate event.
    """
    seen = {(e.content_id, e.timestamp) for e in stored}
    extra = [e for e in incoming if (e.content_id, e.timestamp) not in seen]
    return list(stored) + extra
