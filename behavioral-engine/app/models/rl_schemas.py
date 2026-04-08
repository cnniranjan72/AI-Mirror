"""
Schemas for RL and Alignment system
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# ==================== ALIGNMENT SCHEMAS ====================

class UserGoal(BaseModel):
    """User goal for behavioral alignment"""
    user_id: str
    goal: str
    target_watch_time: Optional[float] = None  # minutes per day
    target_attention_score: Optional[float] = None
    target_engagement_score: Optional[float] = None
    target_activity_level: Optional[float] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AlignmentResponse(BaseModel):
    """Response after setting alignment goal"""
    status: str
    message: str
    goal_id: str
    user_id: str


# ==================== ACTION SCHEMAS ====================

class Action(BaseModel):
    """Behavioral action suggestion"""
    action_id: str
    type: str  # suggestion, intervention, reminder
    description: str
    intensity: str = Field(pattern="^(low|medium|high)$")
    category: str  # time_limit, content_switch, break, mindfulness


class ActionRequest(BaseModel):
    """Request for action suggestion"""
    user_id: str


class ActionResponse(BaseModel):
    """Response with suggested action"""
    action: Action
    state: Dict
    alignment_gap: float
    confidence: float


# ==================== FEEDBACK SCHEMAS ====================

class Feedback(BaseModel):
    """User feedback on action"""
    user_id: str
    action_id: str
    followed: bool
    behavior_change: Optional[float] = None  # -1 to 1
    user_rating: Optional[int] = Field(default=None, ge=1, le=5)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FeedbackResponse(BaseModel):
    """Response after feedback submission"""
    status: str
    message: str
    reward: float
    updated_action_value: float


# ==================== CHAT SCHEMAS ====================

class ChatRequest(BaseModel):
    """Chat query request"""
    user_id: str
    query: str
    include_context: bool = True


class ChatResponse(BaseModel):
    """Chat response with context"""
    response: str
    context_used: List[str]
    persona: Optional[str] = None
    confidence: float
    suggested_actions: Optional[List[str]] = None


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str  # user or assistant
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
