"""
Strongly-typed contracts for AIMirror platform
These models serve as the universal language across all modules
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class EventSource(str, Enum):
    """Source of behavioral event"""
    CHROME_EXTENSION = "chrome_extension"
    DASHBOARD = "dashboard"
    MOBILE_APP = "mobile_app"
    SAVED_REELS = "saved_reels"
    BROWSER_AGENT = "browser_agent"


class ContentType(str, Enum):
    """Type of content"""
    REEL = "reel"
    POST = "post"
    STORY = "story"
    VIDEO = "video"
    ARTICLE = "article"


class MemoryType(str, Enum):
    """Type of memory"""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    BEHAVIORAL = "behavioral"
    GOAL = "goal"
    REFLECTION = "reflection"


class GoalStatus(str, Enum):
    """Status of a goal"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PAUSED = "paused"


# ==================== BEHAVIOR EVENT ====================

class BehaviorEvent(BaseModel):
    """
    Unified behavioral event schema
    All incoming events from any source are normalized to this format
    """
    # Core identification
    event_id: str = Field(..., description="Unique event identifier")
    source: EventSource = Field(..., description="Source of the event")
    timestamp: datetime = Field(..., description="When the event occurred")
    session_id: str = Field(..., description="Session identifier")
    
    # Content identification
    content_id: str = Field(..., description="Unique content identifier (e.g., reel_id)")
    content_type: ContentType = Field(default=ContentType.REEL, description="Type of content")
    
    # Content metadata
    creator: Optional[str] = Field(None, description="Content creator username")
    caption: Optional[str] = Field(None, description="Content caption/description")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags in content")
    audio_info: Optional[str] = Field(None, description="Audio/music information")
    
    # Behavioral metrics
    watch_time: float = Field(..., description="Time spent watching (seconds)")
    liked: bool = Field(default=False, description="Whether user liked the content")
    saved: bool = Field(default=False, description="Whether user saved the content")
    shared: bool = Field(default=False, description="Whether user shared the content")
    commented: bool = Field(default=False, description="Whether user commented")
    replay_count: int = Field(default=0, description="Number of replays")
    scroll_speed: Optional[float] = Field(None, description="Scroll speed metric")
    
    # Context
    device_type: Optional[str] = Field(None, description="Device type (mobile/desktop)")
    platform: str = Field(default="instagram", description="Platform (instagram/tiktok/youtube)")
    
    # Raw data (for future processing)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional raw metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_123abc",
                "source": "chrome_extension",
                "timestamp": "2026-06-11T17:43:00Z",
                "session_id": "sess_456def",
                "content_id": "reel_789ghi",
                "content_type": "reel",
                "creator": "ai_creator",
                "caption": "Amazing AI tutorial",
                "hashtags": ["ai", "tutorial", "tech"],
                "audio_info": "Original Audio",
                "watch_time": 15.5,
                "liked": True,
                "saved": False,
                "shared": False,
                "commented": False,
                "replay_count": 0,
                "scroll_speed": 1.2,
                "device_type": "desktop",
                "platform": "instagram",
                "raw_metadata": {}
            }
        }


# ==================== NORMALIZED CONTENT ====================

class NormalizedContent(BaseModel):
    """
    Normalized content structure from Content Intelligence Layer
    Provider-agnostic representation of extracted content
    """
    # Core fields
    content_id: str = Field(..., description="Unique content identifier")
    source_url: Optional[str] = Field(None, description="Original URL")
    provider: str = Field(..., description="Provider that extracted this content")
    
    # Extracted content
    title: Optional[str] = Field(None, description="Content title")
    caption: Optional[str] = Field(None, description="Content caption/description")
    hashtags: List[str] = Field(default_factory=list, description="Extracted hashtags")
    creator: Optional[str] = Field(None, description="Content creator")
    
    # Intelligence
    topics: List[str] = Field(default_factory=list, description="Identified topics")
    entities: List[str] = Field(default_factory=list, description="Named entities")
    intent: Optional[str] = Field(None, description="Content intent (educate/entertain/inspire)")
    sentiment: Optional[str] = Field(None, description="Sentiment (positive/negative/neutral)")
    language: str = Field(default="en", description="Content language")
    
    # Quality metrics
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")
    completeness: float = Field(..., ge=0.0, le=1.0, description="Data completeness score")
    
    # Metadata
    extracted_at: datetime = Field(..., description="When content was extracted")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_id": "reel_789ghi",
                "source_url": "https://instagram.com/reel/xyz",
                "provider": "playwright",
                "title": "AI Tutorial",
                "caption": "Learn AI in 60 seconds",
                "hashtags": ["ai", "tutorial"],
                "creator": "ai_creator",
                "topics": ["artificial_intelligence", "education"],
                "entities": ["Python", "TensorFlow"],
                "intent": "educate",
                "sentiment": "positive",
                "language": "en",
                "confidence": 0.95,
                "completeness": 0.90,
                "extracted_at": "2026-06-11T17:43:00Z",
                "metadata": {}
            }
        }


# ==================== BEHAVIOR CLUSTER ====================

class BehaviorCluster(BaseModel):
    """
    Consolidated behavioral pattern cluster
    Represents deduplicated, aggregated behavioral memory
    """
    cluster_id: str = Field(..., description="Unique cluster identifier")
    cluster_type: Literal["topic", "creator", "pattern", "trend"] = Field(..., description="Type of cluster")
    
    # Core pattern
    primary_topic: str = Field(..., description="Primary topic/theme")
    related_topics: List[str] = Field(default_factory=list, description="Related topics")
    keywords: List[str] = Field(default_factory=list, description="Key terms")
    
    # Frequency metrics
    occurrence_count: int = Field(..., description="Number of times this pattern occurred")
    first_seen: datetime = Field(..., description="First occurrence")
    last_seen: datetime = Field(..., description="Most recent occurrence")
    
    # Engagement metrics
    avg_watch_time: float = Field(..., description="Average watch time for this cluster")
    engagement_rate: float = Field(..., ge=0.0, le=1.0, description="Engagement rate")
    growth_rate: float = Field(..., description="Growth rate over time")
    
    # Confidence
    confidence: float = Field(..., ge=0.0, le=1.0, description="Cluster confidence score")
    temporal_weight: float = Field(..., ge=0.0, le=1.0, description="Temporal relevance weight")
    
    # Associated data
    event_ids: List[str] = Field(default_factory=list, description="Associated event IDs")
    creators: List[str] = Field(default_factory=list, description="Associated creators")
    
    # Metadata
    created_at: datetime = Field(..., description="When cluster was created")
    updated_at: datetime = Field(..., description="Last update time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ==================== PERSONA ====================

class InterestNode(BaseModel):
    """Node in interest graph"""
    topic: str
    strength: float = Field(..., ge=0.0, le=1.0)
    frequency: int
    last_engaged: datetime


class BehaviorPattern(BaseModel):
    """Behavioral pattern"""
    pattern_type: str
    frequency: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str


class Persona(BaseModel):
    """
    Comprehensive behavioral persona (V2)
    Represents the user's computational identity
    """
    persona_id: str = Field(..., description="Unique persona identifier")
    user_id: str = Field(..., description="Associated user identifier")
    
    # Identity
    archetype: str = Field(..., description="Behavioral archetype")
    archetype_confidence: float = Field(..., ge=0.0, le=1.0, description="Archetype confidence")
    
    # Interest Graph
    primary_interests: List[InterestNode] = Field(default_factory=list, description="Primary interests")
    emerging_interests: List[InterestNode] = Field(default_factory=list, description="Emerging interests")
    declining_interests: List[InterestNode] = Field(default_factory=list, description="Declining interests")
    
    # Behavior Graph
    behavior_patterns: List[BehaviorPattern] = Field(default_factory=list, description="Identified patterns")
    
    # Attention Profile
    avg_attention_span: float = Field(..., description="Average attention span (seconds)")
    attention_consistency: float = Field(..., ge=0.0, le=1.0, description="Attention consistency")
    peak_engagement_times: List[str] = Field(default_factory=list, description="Peak engagement times")
    
    # Learning Style
    learning_style: str = Field(..., description="Preferred learning style")
    content_preferences: Dict[str, float] = Field(default_factory=dict, description="Content type preferences")
    
    # Exploration vs Exploitation
    exploration_score: float = Field(..., ge=0.0, le=1.0, description="Exploration tendency")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="Behavioral consistency")
    
    # Affinity
    creator_affinity: Dict[str, float] = Field(default_factory=dict, description="Creator affinity scores")
    topic_affinity: Dict[str, float] = Field(default_factory=dict, description="Topic affinity scores")
    
    # Strengths & Weaknesses
    strengths: List[str] = Field(default_factory=list, description="Behavioral strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Areas for improvement")
    
    # Confidence & Evolution
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall persona confidence")
    data_points: int = Field(..., description="Number of data points used")
    
    # Evolution Timeline
    created_at: datetime = Field(..., description="When persona was created")
    last_updated: datetime = Field(..., description="Last update time")
    evolution_history: List[Dict[str, Any]] = Field(default_factory=list, description="Evolution snapshots")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ==================== CHARACTER ====================

class Character(BaseModel):
    """
    Virtual Character - User's computational self
    This is NOT chatbot logic, but a representation of the user's digital twin
    """
    character_id: str = Field(..., description="Unique character identifier")
    user_id: str = Field(..., description="Associated user identifier")
    
    # Identity
    name: Optional[str] = Field(None, description="Character name")
    identity_summary: str = Field(..., description="Identity summary")
    
    # Behavior
    behavioral_signature: Dict[str, Any] = Field(default_factory=dict, description="Behavioral signature")
    
    # Goals
    active_goals: List[str] = Field(default_factory=list, description="Active goal IDs")
    goal_alignment_score: float = Field(..., ge=0.0, le=1.0, description="Goal alignment score")
    
    # Memory References
    episodic_memory_refs: List[str] = Field(default_factory=list, description="Episodic memory references")
    semantic_memory_refs: List[str] = Field(default_factory=list, description="Semantic memory references")
    behavioral_memory_refs: List[str] = Field(default_factory=list, description="Behavioral memory references")
    
    # Communication Style
    communication_style: Dict[str, Any] = Field(default_factory=dict, description="Communication preferences")
    
    # Reflection State
    last_reflection: Optional[datetime] = Field(None, description="Last reflection time")
    reflection_frequency: str = Field(default="daily", description="Reflection frequency")
    
    # Confidence
    character_confidence: float = Field(..., ge=0.0, le=1.0, description="Character confidence")
    
    # Current State
    current_persona_id: str = Field(..., description="Current persona ID")
    state: Dict[str, Any] = Field(default_factory=dict, description="Current character state")
    
    # Metadata
    created_at: datetime = Field(..., description="When character was created")
    last_updated: datetime = Field(..., description="Last update time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ==================== MEMORY RECORD ====================

class MemoryRecord(BaseModel):
    """
    Universal memory record
    Can represent any type of memory (episodic, semantic, behavioral, etc.)
    """
    memory_id: str = Field(..., description="Unique memory identifier")
    memory_type: MemoryType = Field(..., description="Type of memory")
    user_id: str = Field(..., description="Associated user identifier")
    
    # Content
    content: str = Field(..., description="Memory content (text representation)")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict, description="Memory context")
    tags: List[str] = Field(default_factory=list, description="Memory tags")
    
    # Temporal
    timestamp: datetime = Field(..., description="When memory was created")
    expires_at: Optional[datetime] = Field(None, description="When memory expires (if applicable)")
    
    # Importance
    importance_score: float = Field(..., ge=0.0, le=1.0, description="Memory importance")
    access_count: int = Field(default=0, description="Number of times accessed")
    last_accessed: Optional[datetime] = Field(None, description="Last access time")
    
    # Associations
    related_memory_ids: List[str] = Field(default_factory=list, description="Related memory IDs")
    source_event_ids: List[str] = Field(default_factory=list, description="Source event IDs")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ==================== GOAL STATE ====================

class GoalState(BaseModel):
    """
    User goal state
    Represents a user's goal and progress toward it
    """
    goal_id: str = Field(..., description="Unique goal identifier")
    user_id: str = Field(..., description="Associated user identifier")
    
    # Goal definition
    goal_description: str = Field(..., description="Natural language goal description")
    goal_type: str = Field(..., description="Type of goal (learning/behavioral/content)")
    
    # Status
    status: GoalStatus = Field(..., description="Current goal status")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress toward goal (0-1)")
    
    # Alignment
    alignment_score: float = Field(..., ge=0.0, le=1.0, description="Current behavior alignment with goal")
    supporting_behaviors: List[str] = Field(default_factory=list, description="Behaviors supporting goal")
    conflicting_behaviors: List[str] = Field(default_factory=list, description="Behaviors conflicting with goal")
    
    # Temporal
    created_at: datetime = Field(..., description="When goal was created")
    target_date: Optional[datetime] = Field(None, description="Target completion date")
    completed_at: Optional[datetime] = Field(None, description="When goal was completed")
    last_updated: datetime = Field(..., description="Last update time")
    
    # Tracking
    milestones: List[Dict[str, Any]] = Field(default_factory=list, description="Goal milestones")
    related_event_ids: List[str] = Field(default_factory=list, description="Related event IDs")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ==================== REFLECTION ====================

class Reflection(BaseModel):
    """
    System reflection
    Represents a periodic reflection on user behavior
    """
    reflection_id: str = Field(..., description="Unique reflection identifier")
    user_id: str = Field(..., description="Associated user identifier")
    
    # Type
    reflection_type: Literal["daily", "weekly", "monthly", "custom"] = Field(..., description="Reflection type")
    
    # Period
    period_start: datetime = Field(..., description="Start of reflection period")
    period_end: datetime = Field(..., description="End of reflection period")
    
    # Summary
    summary: str = Field(..., description="Natural language summary")
    key_insights: List[str] = Field(default_factory=list, description="Key insights")
    
    # Metrics
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Period metrics")
    
    # Patterns
    patterns_identified: List[str] = Field(default_factory=list, description="Identified patterns")
    changes_detected: List[str] = Field(default_factory=list, description="Detected changes")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    
    # Confidence
    confidence: float = Field(..., ge=0.0, le=1.0, description="Reflection confidence")
    
    # References
    event_count: int = Field(..., description="Number of events analyzed")
    memory_refs: List[str] = Field(default_factory=list, description="Referenced memories")
    
    # Metadata
    created_at: datetime = Field(..., description="When reflection was created")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
