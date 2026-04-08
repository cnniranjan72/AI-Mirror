"""
Feature engineering service for behavioral data
Converts raw events into meaningful summaries and traits
"""
from typing import List
from datetime import datetime
import statistics
import logging
from app.models.schemas import BehavioralEvent, SessionSummary, BehavioralTraits

logger = logging.getLogger(__name__)


def compute_session_summary(events: List[BehavioralEvent]) -> SessionSummary:
    """
    Aggregate events into a session-level summary
    
    Args:
        events: List of behavioral events from a single session
        
    Returns:
        SessionSummary with aggregated metrics
    """
    if not events:
        raise ValueError("Cannot compute summary for empty event list")
    
    # Extract session_id (all events should have same session_id)
    session_id = events[0].session_id
    
    # Compute metrics
    total_watch_time = sum(event.watch_time for event in events)
    avg_watch_time = total_watch_time / len(events)
    
    # Like ratio
    liked_count = sum(1 for event in events if event.liked)
    like_ratio = liked_count / len(events) if len(events) > 0 else 0.0
    
    # Reels count
    reels_count = len(events)
    
    # Session duration (time between first and last event)
    timestamps = [datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')) for event in events]
    session_duration = (max(timestamps) - min(timestamps)).total_seconds()
    
    # Collect metadata from events
    captions = [event.caption for event in events if event.caption]
    all_hashtags = []
    audio_infos = []
    
    for event in events:
        if event.hashtags:
            all_hashtags.extend(event.hashtags)
        if event.audio_info:
            audio_infos.append(event.audio_info)
    
    # Get unique hashtags
    unique_hashtags = list(set(all_hashtags))
    
    # Get most common audio info
    most_common_audio = max(set(audio_infos), key=audio_infos.count) if audio_infos else ""
    
    return SessionSummary(
        session_id=session_id,
        total_watch_time=round(total_watch_time, 2),
        avg_watch_time=round(avg_watch_time, 2),
        like_ratio=round(like_ratio, 2),
        reels_count=reels_count,
        session_duration=round(session_duration, 2),
        captions=captions[:5],  # First 5 captions
        hashtags=unique_hashtags[:10],  # Top 10 unique hashtags
        audio_info=most_common_audio
    )


def compute_behavioral_traits(events: List[BehavioralEvent]) -> BehavioralTraits:
    """
    Compute behavioral traits from events
    
    Args:
        events: List of behavioral events
        
    Returns:
        BehavioralTraits with computed scores
    """
    if not events:
        raise ValueError("Cannot compute traits for empty event list")
    
    session_id = events[0].session_id
    
    # Attention score: normalized average watch time
    # Assume max watch time of 60 seconds for normalization
    avg_watch_time = sum(event.watch_time for event in events) / len(events)
    attention_score = min(avg_watch_time / 60.0, 1.0)
    
    # Engagement score: like ratio
    liked_count = sum(1 for event in events if event.liked)
    engagement_score = liked_count / len(events) if len(events) > 0 else 0.0
    
    # Activity level: reels count (normalized by session duration)
    timestamps = [datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')) for event in events]
    session_duration = (max(timestamps) - min(timestamps)).total_seconds()
    activity_level = len(events) / max(session_duration / 60.0, 1.0)  # reels per minute
    
    # Analyze captions and hashtags
    all_captions = [event.caption for event in events if event.caption]
    all_hashtags = []
    for event in events:
        if event.hashtags:
            all_hashtags.extend(event.hashtags)
    
    # Content diversity: unique hashtags / total hashtags
    unique_hashtags = len(set(all_hashtags)) if all_hashtags else 0
    content_diversity = unique_hashtags / len(all_hashtags) if all_hashtags else 0
    
    # Caption length analysis
    avg_caption_length = sum(len(caption) for caption in all_captions) / len(all_captions) if all_captions else 0
    
    logger.info(f"Session {session_id}: {len(all_hashtags)} hashtags, {unique_hashtags} unique, diversity: {content_diversity:.2f}")
    
    return BehavioralTraits(
        session_id=session_id,
        attention_score=round(attention_score, 3),
        engagement_score=round(engagement_score, 3),
        activity_level=round(activity_level, 2),
        content_diversity=round(content_diversity, 2),
        avg_caption_length=round(avg_caption_length, 2),
        timestamp=datetime.utcnow().isoformat()
    )


def summary_to_text(summary: SessionSummary) -> str:
    """
    Convert session summary to natural language text for embedding
    
    Args:
        summary: SessionSummary object
        
    Returns:
        Natural language description
    """
    text = (
        f"User watched {summary.reels_count} reels with average watch time "
        f"{summary.avg_watch_time} seconds and like ratio {summary.like_ratio}. "
        f"Total watch time was {summary.total_watch_time} seconds over "
        f"{summary.session_duration} seconds of session duration."
    )
    
    # Add caption information if available
    if hasattr(summary, 'captions') and summary.captions:
        captions_text = " | ".join(summary.captions[:2])  # First 2 captions
        text += f" Captions: {captions_text}"
    
    if hasattr(summary, 'hashtags') and summary.hashtags:
        hashtags_text = ", ".join(summary.hashtags[:5])  # First 5 hashtags
        text += f" Hashtags: {hashtags_text}"
    
    return text


def traits_to_text(traits: BehavioralTraits) -> str:
    """
    Convert behavioral traits to natural language text for embedding
    
    Args:
        traits: BehavioralTraits object
        
    Returns:
        Natural language description
    """
    text = (
        f"User behavioral traits: attention score {traits.attention_score}, "
        f"engagement score {traits.engagement_score}, "
        f"activity level {traits.activity_level} reels per minute"
    )
    
    # Add content diversity if available
    if hasattr(traits, 'content_diversity'):
        text += f", content diversity {traits.content_diversity}"
    
    # Add caption length if available
    if hasattr(traits, 'avg_caption_length'):
        text += f", avg caption length {traits.avg_caption_length}"
    
    return text


def group_events_by_session(events: List[BehavioralEvent]) -> dict:
    """
    Group events by session_id
    
    Args:
        events: List of behavioral events
        
    Returns:
        Dictionary mapping session_id to list of events
    """
    sessions = {}
    for event in events:
        if event.session_id not in sessions:
            sessions[event.session_id] = []
        sessions[event.session_id].append(event)
    
    return sessions
