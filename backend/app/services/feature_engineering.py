"""
Feature Engineering Service
Computes behavioral traits from raw event data.
"""

import logging
from typing import Dict, List, Any
from collections import Counter

logger = logging.getLogger(__name__)


def compute_features(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute behavioral features from a batch of events.

    Returns:
        Dictionary of computed features and behavioral summary text.
    """
    if not events:
        return _empty_features()

    watch_times = [e.get("watch_time", 0) for e in events]
    usernames = [e.get("username", "unknown") for e in events]
    all_hashtags = []
    for e in events:
        tags = e.get("hashtags", [])
        if isinstance(tags, list):
            all_hashtags.extend(tags)

    total_watch = sum(watch_times)
    avg_watch = total_watch / len(watch_times) if watch_times else 0
    max_watch = max(watch_times) if watch_times else 0
    min_watch = min(watch_times) if watch_times else 0

    # Attention score: ratio of avg watch time to max (0-1)
    attention = min(avg_watch / 30.0, 1.0)  # normalize to 30s baseline

    # Engagement: variety of creators watched
    unique_creators = len(set(usernames))
    engagement = min(unique_creators / max(len(events), 1), 1.0)

    # Content diversity: unique hashtag ratio
    unique_tags = len(set(all_hashtags))
    diversity = min(unique_tags / max(len(all_hashtags), 1), 1.0) if all_hashtags else 0

    # Curiosity: how spread the watch times are (low variance = passive)
    if len(watch_times) > 1:
        mean_wt = avg_watch
        variance = sum((w - mean_wt) ** 2 for w in watch_times) / len(watch_times)
        curiosity = min(variance ** 0.5 / 15.0, 1.0)  # normalize
    else:
        curiosity = 0.0

    top_creators = [c for c, _ in Counter(usernames).most_common(5)]
    top_hashtags = [h for h, _ in Counter(all_hashtags).most_common(10)]

    features = {
        "total_events": len(events),
        "total_watch_time": round(total_watch, 2),
        "avg_watch_time": round(avg_watch, 2),
        "max_watch_time": round(max_watch, 2),
        "min_watch_time": round(min_watch, 2),
        "unique_creators": unique_creators,
        "unique_hashtags": unique_tags,
        "attention_score": round(attention, 3),
        "engagement_score": round(engagement, 3),
        "content_diversity": round(diversity, 3),
        "curiosity_score": round(curiosity, 3),
        "top_creators": top_creators,
        "top_hashtags": top_hashtags,
    }

    # Behavioral summary text (embeddable)
    features["summary_text"] = _build_summary(features)

    logger.debug("Computed features for %d events", len(events))
    return features


def _build_summary(f: Dict[str, Any]) -> str:
    parts = [
        f"User watched {f['total_events']} reels with total watch time {f['total_watch_time']:.0f}s.",
        f"Average watch time {f['avg_watch_time']:.1f}s per reel.",
        f"Attention score {f['attention_score']:.2f}, engagement {f['engagement_score']:.2f}.",
        f"Content diversity {f['content_diversity']:.2f}, curiosity {f['curiosity_score']:.2f}.",
    ]
    if f["top_creators"]:
        parts.append(f"Top creators: {', '.join(f['top_creators'][:3])}.")
    if f["top_hashtags"]:
        parts.append(f"Top hashtags: {', '.join(f['top_hashtags'][:5])}.")
    return " ".join(parts)


def _empty_features() -> Dict[str, Any]:
    return {
        "total_events": 0,
        "total_watch_time": 0,
        "avg_watch_time": 0,
        "max_watch_time": 0,
        "min_watch_time": 0,
        "unique_creators": 0,
        "unique_hashtags": 0,
        "attention_score": 0,
        "engagement_score": 0,
        "content_diversity": 0,
        "curiosity_score": 0,
        "top_creators": [],
        "top_hashtags": [],
        "summary_text": "No behavioral data available yet.",
    }
