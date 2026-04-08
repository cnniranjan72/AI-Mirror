"""
Pydantic schemas for behavioral intelligence engine
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ==================== INPUT SCHEMAS ====================

class BehavioralEvent(BaseModel):
    """Single behavioral event from Chrome extension"""
    reel_id: str
    username: str
    caption: Optional[str] = ""
    hashtags: Optional[List[str]] = []
    audio_info: Optional[str] = ""
    watch_time: float
    liked: Optional[bool] = False
    timestamp: str
    session_id: str


class EventBatch(BaseModel):
    """Batch of events for ingestion"""
    events: List[BehavioralEvent]


# ==================== SUMMARY SCHEMAS ====================

class SessionSummary(BaseModel):
    """Aggregated session-level summary"""
    type: str = "session_summary"
    session_id: str
    total_watch_time: float
    avg_watch_time: float
    like_ratio: float
    reels_count: int
    session_duration: float
    captions: Optional[List[str]] = []
    hashtags: Optional[List[str]] = []
    audio_info: Optional[str] = ""


class BehavioralTraits(BaseModel):
    """Computed behavioral traits"""
    type: str = "behavioral_traits"
    session_id: str
    attention_score: float = Field(..., ge=0.0, le=1.0)
    engagement_score: float = Field(..., ge=0.0, le=1.0)
    activity_level: float
    content_diversity: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_caption_length: float = Field(default=0.0)
    timestamp: str


# ==================== QUERY SCHEMAS ====================

class QueryRequest(BaseModel):
    """Query request for behavioral insights"""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResult(BaseModel):
    """Single query result"""
    text: str
    score: float
    metadata: dict


class QueryResponse(BaseModel):
    """Query response with results and optional insight"""
    results: List[QueryResult]
    query: str
    insight: Optional[dict] = None


# ==================== INGEST RESPONSE ====================

class IngestResponse(BaseModel):
    """Response after ingesting events"""
    status: str
    events_processed: int
    summaries_created: int
    embeddings_stored: int
    message: str
