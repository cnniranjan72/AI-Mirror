"""
POST /seed — One-click demo data seeding for live demos.
Generates synthetic Instagram behavioral data and runs it through the V3 pipeline.
"""
import json
import logging
import random
import string
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends

from app.db.postgres import execute, fetch
from backend.shared.contracts import EventSource
from app.core.rate_limit import seed_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()

TOPICS = [
    "Artificial Intelligence", "Machine Learning", "Software Engineering",
    "Data Science", "Productivity", "Entrepreneurship", "Design",
    "Photography", "Travel", "Fitness", "Cooking", "Music Production",
    "Gaming", "Reading", "Philosophy", "Psychology",
]

CREATORS = [
    "tech_with_tom", "ai_daily", "codecraft", "datascience_pro",
    "design_mastery", "photo_artist", "travel_adventures",
    "fitness_guru", "cooking_master", "music_producer",
    "gaming_world", "book_club", "philosophy_talks",
    "psychology_insights", "startup_stories", "creative_coding",
]

HASHTAGS = [
    "#tech", "#ai", "#coding", "#design", "#photography", "#travel",
    "#fitness", "#cooking", "#music", "#gaming", "#reading",
    "#philosophy", "#psychology", "#startup", "#productivity",
]

AUDIO_TRACKS = [
    "sunset_vibes.mp3", "lofi_study.mp3", "chill_morning.mp3",
    "deep_focus.mp3", "energy_boost.mp3", "ambient_space.mp3",
]


def _random_user_id() -> str:
    return f"demo_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"


# A demo user with uniformly random interests has no interests: every rule
# sees a flat distribution, PrimaryInterestRule finds no primary interest, and
# the twin has nothing to say. Real attention is skewed, so the demo profile is
# too — a few things they clearly care about, a mid band, and a long tail.
#
# The weights also give the Algorithmic Mirror something real to check: DEMO_-
# CLAIMS below is written against this shape, so some platform claims are
# corroborated by behaviour and some are not.
CORE_TOPICS = ["Artificial Intelligence", "Machine Learning", "Photography"]
MID_TOPICS = ["Travel", "Cooking", "Software Engineering"]

CORE_CREATORS = ["ai_daily", "tech_with_tom", "photo_artist"]


def _weighted_topic() -> str:
    roll = random.random()
    if roll < 0.45:
        return random.choice(CORE_TOPICS)
    if roll < 0.75:
        return random.choice(MID_TOPICS)
    return random.choice(TOPICS)


def _weighted_creator() -> str:
    # Concentrated enough to be visible, not so concentrated that
    # CreatorDiversityRule and CreatorDependenceRule both fire on everything.
    return random.choice(CORE_CREATORS) if random.random() < 0.4 else random.choice(CREATORS)


def _generate_events(user_id: str, count: int = 800) -> List[dict]:
    events = []
    base = datetime.now() - timedelta(days=30)
    for i in range(count):
        # Strictly in the past. base is now-30d and the old bounds added up to
        # 30 days PLUS an hour, so roughly one seeded event in 720 landed in
        # the future — enough to trip the recency_score clamp and, before that
        # clamp existed, to discard every behaviour object for the run.
        ts = base + timedelta(minutes=random.randint(0, 30 * 24 * 60 - 60))
        topic = _weighted_topic()
        creator = _weighted_creator()
        watch_time = random.gauss(45, 30)
        watch_time = max(3, min(300, watch_time))
        events.append({
            "reel_id": f"demo_reel_{i:04d}",
            "username": creator,
            # No word common to every caption. The old template was
            # "{topic} content — exploring ..." and "content" appeared in all
            # 800, which is enough for it to survive topic selection and
            # become a behaviour object of its own — the same boilerplate-topic
            # failure the real taxonomy guards against, manufactured by the
            # demo's own data.
            "caption": f"{topic}: {random.choice(['a walkthrough', 'the basics', 'an advanced look', 'field notes', 'a case study'])}",
            "hashtags": random.sample(HASHTAGS, random.randint(1, 4)),
            "audio": random.choice(AUDIO_TRACKS),
            "watch_time": round(watch_time, 1),
            "timestamp": ts.isoformat(),
            "session_id": f"demo_session_{random.randint(0, 20)}",
            "source_url": f"https://instagram.com/reel/demo_reel_{i:04d}",
        })
    events.sort(key=lambda e: e["timestamp"])
    return events


async def _store_events(user_id: str, events: List[dict]):
    """Insert the whole batch in one statement, and return the row ids.

    This was 800 single-row INSERTs, each its own round trip. Measured against
    the managed database that is around 100-350 s of pure latency, in a request
    that still has to run the entire pipeline afterwards - and roughly half of
    them never got that far. Of 15 demo accounts, 7 hold events and no
    behaviour objects, four of those with all 800 events stored: the inserts
    finished and the request died before consolidation. Such an account is
    permanently unanswerable, since nothing ever revisits stored events, and
    every question it is asked returns "No behavioral data found yet".

    unnest makes it one round trip. RETURNING hands back the ids the pipeline
    needs to link behaviour objects to the events behind them; the mapping is
    keyed by content id, so the order rows come back in does not matter.

    A malformed row now fails the whole seed rather than being logged and
    skipped. That is deliberate: a seed that half-succeeds is the defect being
    fixed here, and an error the caller can see beats an account that looks
    real and answers nothing.
    """
    rows = await fetch(
        """
        INSERT INTO events (user_id, reel_id, username, caption, hashtags,
                            audio, watch_time, timestamp, session_id)
        SELECT $1, r, u, c, h::jsonb, a, w, t, s
        FROM unnest($2::text[], $3::text[], $4::text[], $5::text[], $6::text[],
                    $7::double precision[], $8::timestamptz[], $9::text[])
             AS e(r, u, c, h, a, w, t, s)
        RETURNING id, reel_id
        """,
        user_id,
        [e["reel_id"] for e in events],
        [e["username"] for e in events],
        [e["caption"] for e in events],
        [json.dumps(e["hashtags"]) for e in events],
        [e["audio"] for e in events],
        [float(e["watch_time"]) for e in events],
        [datetime.fromisoformat(e["timestamp"]) for e in events],
        [e["session_id"] for e in events],
    )
    return len(rows), {r["reel_id"]: r["id"] for r in rows}


async def _run_pipeline(user_id: str, events: List[dict], reel_id_to_db_id: dict):
    try:
        from backend.core.behavior_gateway import get_behavior_gateway
        from pipeline.orchestrator import V3Pipeline

        gateway = get_behavior_gateway()
        normalized = gateway.process_batch({"events": events}, EventSource.CHROME_EXTENSION)

        # Same fix as /ingest: point each BehaviorEvent's event_id at the real
        # events.id row instead of the normalizer's random evt_xxxx, so the
        # Timeline endpoint's supporting_event_ids reverse-index works on
        # demo-seeded data too.
        for bev in normalized:
            db_id = reel_id_to_db_id.get(bev.content_id)
            if db_id is not None:
                bev.event_id = str(db_id)

        pipeline = V3Pipeline()
        result = await pipeline.run(user_id, normalized)

        logger.info(f"Demo pipeline complete: {len(events)} events → {len(result.evidence)} evidence, "
                     f"{len(result.inferences)} inferences, "
                     f"identity v{result.identity.identity_version if result.identity else '?'}")
        return result
    except Exception as e:
        logger.error(f"Demo pipeline error: {e}")
        raise


# What the platform SAYS about this person, for the Algorithmic Mirror to
# check. Written against the profile shape above so the demo shows a real
# mix rather than a trivially perfect or trivially empty result:
#
#   corroborated   — the behaviour supports it
#   unsupported    — the platform asserts an interest with nothing behind it,
#                    which is the finding the Mirror exists to surface
#   not_comparable — demographic or life-event guesses a watch history can
#                    neither confirm nor refute (see _NON_TESTABLE_PATTERNS)
#
# Synthetic, and only ever written to a freshly minted demo_* account.
DEMO_CLAIMS = [
    ("meta", "Artificial intelligence"),
    ("meta", "Photography"),
    ("meta", "Travel"),
    ("google", "Machine learning"),
    # Nothing in the generated behaviour supports these.
    ("meta", "Luxury goods"),
    ("meta", "Cryptocurrency"),
    ("google", "Automotive"),
    # Not testable from a watch history at all.
    ("meta", "Frequent travellers"),
    ("google", "Mobile device users"),
]

# What this person went looking for, for Interest Provenance. Searching is a
# deliberate act, so an interest with searches behind it was CHOSEN; heavy
# exposure with no searches is the signature of something FED. Cooking is
# deliberately absent from this list while appearing often in the events.
DEMO_SEARCHES = [
    "machine learning tutorial", "transformer architecture explained",
    "pytorch vs tensorflow", "neural network basics",
    "photography lighting setup", "50mm lens portrait tips",
    "camera settings for low light",
    "kyoto itinerary", "cheap flights to lisbon",
]


async def _seed_platform_side(user_id: str) -> dict:
    """Populate what the twin does not generate: the platform's own claims and
    the user's searches.

    Without these the Algorithmic Mirror has nothing to audit and Interest
    Provenance cannot tell a chosen interest from a fed one — so the three
    features the product is actually about are blank in its own demo.

    Verdicts are deliberately NOT seeded. Those are the user's judgements of
    the system, and the Accuracy Ledger's whole claim is that its score comes
    from what a real person said. Fabricating them would make the one number
    that measures honesty dishonest. The demo shows the Ledger's real empty
    state and invites the visitor to answer.
    """
    claims = searches = 0
    for platform, label in DEMO_CLAIMS:
        try:
            await execute(
                """INSERT INTO platform_profile_claims
                       (user_id, platform, claim_type, label, raw_label, source_file)
                   VALUES ($1, $2, 'ad_interest', $3, $4, 'demo_seed')
                   ON CONFLICT DO NOTHING""",
                user_id, platform, label.lower().strip(), label,
            )
            claims += 1
        except Exception as e:
            logger.warning(f"Demo claim seed failed ({label}): {e}")

    base = datetime.now() - timedelta(days=30)
    for i, query in enumerate(DEMO_SEARCHES):
        try:
            await execute(
                """INSERT INTO search_signals
                       (user_id, platform, query, raw_query, searched_at, source_file)
                   VALUES ($1, 'google', $2, $3, $4, 'demo_seed')
                   ON CONFLICT DO NOTHING""",
                user_id, query.lower().strip(), query,
                base + timedelta(days=i * 3, hours=random.randint(0, 23)),
            )
            searches += 1
        except Exception as e:
            logger.warning(f"Demo search seed failed ({query}): {e}")

    return {"platform_claims": claims, "search_signals": searches}


@router.post("/seed", dependencies=[Depends(seed_rate_limit)])
async def seed_demo_data():
    user_id = _random_user_id()
    events = _generate_events(user_id, 800)

    stored, reel_id_to_db_id = await _store_events(user_id, events)

    result = await _run_pipeline(user_id, events, reel_id_to_db_id)
    platform_side = await _seed_platform_side(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "events_stored": stored,
        "platform_side": platform_side,
        "pipeline_result": {
            "evidence_count": len(result.evidence),
            "inference_count": len(result.inferences),
            "reflection_count": 1 if result.reflection else 0,
            "identity_version": result.identity.identity_version if result.identity else None,
            "behavior_object_count": len(result.behavior_objects),
        },
    }
