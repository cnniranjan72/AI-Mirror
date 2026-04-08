from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EventData(BaseModel):
    reel_id: str
    username: Optional[str] = "unknown_user"
    caption: Optional[str] = ""
    liked: bool = False
    watch_time: float = Field(..., ge=0)
    replay_count: int = Field(default=0, ge=0)
    scroll_speed: float = Field(default=0.0, ge=0)
    timestamp: str

class SessionData(BaseModel):
    session_id: str
    start_time: str
    end_time: str
    events: List[EventData]

class SessionResponse(BaseModel):
    id: int
    session_id: str
    start_time: datetime
    end_time: datetime
    total_events: int
    total_watch_time: float
    created_at: datetime

    class Config:
        from_attributes = True

class EventResponse(BaseModel):
    id: int
    session_id: str
    reel_id: str
    username: Optional[str]
    caption: Optional[str]
    liked: bool
    watch_time: float
    replay_count: int
    scroll_speed: float
    timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_events: int
    total_watch_time: float
    avg_watch_time_per_reel: float
    avg_watch_time_per_session: float
    like_ratio: float
    avg_scroll_speed: float
    reels_per_session: float
    most_watched_users: List[dict]
    total_replays: int
