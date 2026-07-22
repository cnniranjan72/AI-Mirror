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

from fastapi import APIRouter

from app.db.postgres import execute, fetch, fetchrow
from backend.shared.contracts import EventSource

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


def _generate_events(user_id: str, count: int = 800) -> List[dict]:
    events = []
    base = datetime.now() - timedelta(days=30)
    for i in range(count):
        ts = base + timedelta(
            minutes=random.randint(0, 30 * 24 * 60),
            seconds=random.randint(0, 3600),
        )
        topic = random.choice(TOPICS)
        creator = random.choice(CREATORS)
        watch_time = random.gauss(45, 30)
        watch_time = max(3, min(300, watch_time))
        events.append({
            "reel_id": f"demo_reel_{i:04d}",
            "username": creator,
            "caption": f"{topic} content — exploring {random.choice(['new ideas', 'advanced concepts', 'tutorials', 'inspiration', 'case studies'])}",
            "hashtags": random.sample(HASHTAGS, random.randint(1, 4)),
            "audio": random.choice(AUDIO_TRACKS),
            "watch_time": round(watch_time, 1),
            "timestamp": ts.isoformat(),
            "session_id": f"demo_session_{random.randint(0, 20)}",
            "source_url": f"https://instagram.com/reel/demo_reel_{i:04d}",
        })
    events.sort(key=lambda e: e["timestamp"])
    return events


async def _run_pipeline(user_id: str, events: List[dict]):
    try:
        from backend.core.behavior_gateway import get_behavior_gateway
        from pipeline.orchestrator import V3Pipeline

        gateway = get_behavior_gateway()
        normalized = await gateway.process_batch({"events": events}, EventSource.CHROME_EXTENSION)

        pipeline = V3Pipeline()
        result = await pipeline.run(user_id, normalized)

        logger.info(f"Demo pipeline complete: {len(events)} events → {result.get('evidence_count', 0)} evidence, "
                     f"{result.get('inference_count', 0)} inferences, "
                     f"identity v{result.get('identity_version', '?')}")
        return result
    except Exception as e:
        logger.error(f"Demo pipeline error: {e}")
        raise


@router.post("/seed")
async def seed_demo_data():
    user_id = _random_user_id()
    events = _generate_events(user_id, 800)

    stored = 0
    for event in events:
        try:
            await execute(
                """INSERT INTO events (user_id, reel_id, username, caption, hashtags, audio, watch_time, timestamp, session_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                user_id, event["reel_id"], event["username"], event["caption"],
                json.dumps(event["hashtags"]), event["audio"], event["watch_time"],
                event["timestamp"], event["session_id"],
            )
            stored += 1
        except Exception as e:
            logger.warning(f"Failed to store event {event['reel_id']}: {e}")

    result = await _run_pipeline(user_id, events)

    return {
        "success": True,
        "user_id": user_id,
        "events_stored": stored,
        "pipeline_result": {
            "evidence_count": result.get("evidence_count", 0),
            "inference_count": result.get("inference_count", 0),
            "reflection_count": result.get("reflection_count", 0),
            "identity_version": result.get("identity_version"),
            "behavior_object_count": result.get("behavior_object_count", 0),
        },
    }
