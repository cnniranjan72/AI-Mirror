"""
Behavior Object Model
Canonical representation of user behavior for downstream reasoning
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum


def _ensure_aware(dt: datetime) -> datetime:
    """Coerce a possibly-naive datetime to UTC-aware. Data persisted before
    the timestamp-normalization fix stored naive datetimes; anything written
    since is aware — this dataset is permanently mixed, so every comparison
    against datetime.now(timezone.utc) needs this rather than trusting the
    stored value's format."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class BehaviorLifecycleState(str, Enum):
    """Lifecycle state of a behavior object"""
    EMERGING = "emerging"
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"
    DORMANT = "dormant"
    ARCHIVED = "archived"


class TrendDirection(str, Enum):
    """Direction of behavioral trend (deprecated - use BehaviorLifecycleState)"""
    EMERGING = "emerging"
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"
    DORMANT = "dormant"


class EngagementStatistics(BaseModel):
    """Engagement metrics for a behavior"""
    total_interactions: int = Field(..., description="Total number of interactions")
    like_rate: float = Field(..., ge=0.0, le=1.0, description="Percentage of liked content")
    save_rate: float = Field(..., ge=0.0, le=1.0, description="Percentage of saved content")
    share_rate: float = Field(..., ge=0.0, le=1.0, description="Percentage of shared content")
    comment_rate: float = Field(..., ge=0.0, le=1.0, description="Percentage of commented content")
    overall_engagement_rate: float = Field(..., ge=0.0, le=1.0, description="Overall engagement rate")
    engagement_quality_score: float = Field(..., ge=0.0, le=1.0, description="Quality of engagement")


class WatchStatistics(BaseModel):
    """Watch time metrics for a behavior"""
    total_watch_time: float = Field(..., description="Total watch time in seconds")
    avg_watch_time: float = Field(..., description="Average watch time per content")
    median_watch_time: float = Field(..., description="Median watch time")
    max_watch_time: float = Field(..., description="Maximum watch time")
    min_watch_time: float = Field(..., description="Minimum watch time")
    watch_time_std: float = Field(..., description="Standard deviation of watch time")
    completion_rate: float = Field(..., ge=0.0, le=1.0, description="Estimated completion rate")


class TemporalStatistics(BaseModel):
    """Temporal patterns for a behavior"""
    first_seen: datetime = Field(..., description="First occurrence")
    last_seen: datetime = Field(..., description="Most recent occurrence")
    days_active: int = Field(..., description="Number of days this behavior has been active")
    occurrence_count: int = Field(..., description="Total number of occurrences")
    daily_frequency: float = Field(..., description="Average occurrences per day")
    weekly_frequency: float = Field(..., description="Average occurrences per week")
    recency_score: float = Field(..., ge=0.0, le=1.0, description="How recent this behavior is")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="How consistent this behavior is")


class TrendInformation(BaseModel):
    """Trend analysis for a behavior"""
    trend_direction: TrendDirection = Field(..., description="Direction of trend")
    growth_rate: float = Field(..., description="Rate of growth/decline")
    momentum_score: float = Field(..., ge=0.0, le=1.0, description="Strength of trend momentum")
    volatility_score: float = Field(..., ge=0.0, le=1.0, description="Volatility of behavior")
    prediction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in trend prediction")
    expected_trajectory: str = Field(..., description="Expected future trajectory")


class EvolutionSnapshot(BaseModel):
    """Snapshot of behavior at a point in time"""
    timestamp: datetime = Field(..., description="When snapshot was taken")
    occurrence_count: int = Field(..., description="Occurrence count at this time")
    engagement_rate: float = Field(..., ge=0.0, le=1.0, description="Engagement rate at this time")
    avg_watch_time: float = Field(..., description="Average watch time at this time")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence at this time")
    notable_change: Optional[str] = Field(None, description="Notable change at this point")


class BehaviorObject(BaseModel):
    """
    Canonical representation of user behavior
    
    This is the primary data structure for behavioral understanding.
    All downstream reasoning (Persona, Character, RAG, RL) consumes BehaviorObjects.
    
    BehaviorObjects replace raw clusters and provide a rich, evolving representation
    of user behavioral patterns.
    """
    # Core identification
    unique_id: str = Field(..., description="Unique behavior object identifier")
    topic: str = Field(..., description="Primary topic/theme of this behavior")
    subtopics: List[str] = Field(default_factory=list, description="Related subtopics")
    
    # Semantic representation
    representative_embedding: List[float] = Field(..., description="Representative embedding vector")
    keywords: List[str] = Field(default_factory=list, description="Key terms associated with behavior")
    
    # Associated entities
    creators: List[str] = Field(default_factory=list, description="Content creators associated with behavior")
    creator_diversity_score: float = Field(..., ge=0.0, le=1.0, description="Diversity of creators")
    
    # Statistics
    engagement_statistics: EngagementStatistics = Field(..., description="Engagement metrics")
    watch_statistics: WatchStatistics = Field(..., description="Watch time metrics")
    temporal_statistics: TemporalStatistics = Field(..., description="Temporal patterns")
    trend_information: TrendInformation = Field(..., description="Trend analysis")
    
    # Lifecycle
    lifecycle_state: BehaviorLifecycleState = Field(..., description="Current lifecycle state")
    
    # Importance and confidence
    importance_score: float = Field(..., ge=0.0, le=1.0, description="Overall importance of this behavior")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in this behavior pattern")
    stability_score: float = Field(..., ge=0.0, le=1.0, description="Stability of this behavior over time")
    
    # Evidence
    evidence_references: List[str] = Field(default_factory=list, description="References to supporting evidence")
    supporting_event_ids: List[str] = Field(default_factory=list, description="IDs of supporting events")
    supporting_cluster_ids: List[str] = Field(default_factory=list, description="IDs of supporting clusters")
    
    # Evolution tracking
    evolution_history: List[EvolutionSnapshot] = Field(default_factory=list, description="Historical snapshots")
    version: int = Field(default=1, description="Version number for tracking updates")
    
    # Metadata
    created_at: datetime = Field(..., description="When behavior object was created")
    updated_at: datetime = Field(..., description="Last update time")
    last_accessed: Optional[datetime] = Field(None, description="Last time this was accessed")
    access_count: int = Field(default=0, description="Number of times accessed")
    
    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Categorical tags")
    
    class Config:
        json_schema_extra = {
            "example": {
                "unique_id": "behavior_ai_learning_abc123",
                "topic": "AI Learning",
                "subtopics": ["machine learning", "deep learning", "neural networks"],
                "representative_embedding": [0.1, 0.2, 0.3],
                "keywords": ["ai", "ml", "tutorial", "learning"],
                "creators": ["ai_educator", "ml_expert", "tech_teacher"],
                "creator_diversity_score": 0.75,
                "engagement_statistics": {
                    "total_interactions": 50,
                    "like_rate": 0.8,
                    "save_rate": 0.6,
                    "share_rate": 0.2,
                    "comment_rate": 0.1,
                    "overall_engagement_rate": 0.75,
                    "engagement_quality_score": 0.85
                },
                "watch_statistics": {
                    "total_watch_time": 750.0,
                    "avg_watch_time": 15.0,
                    "median_watch_time": 14.5,
                    "max_watch_time": 30.0,
                    "min_watch_time": 5.0,
                    "watch_time_std": 4.2,
                    "completion_rate": 0.9
                },
                "temporal_statistics": {
                    "first_seen": "2026-05-01T00:00:00Z",
                    "last_seen": "2026-06-11T00:00:00Z",
                    "days_active": 41,
                    "occurrence_count": 50,
                    "daily_frequency": 1.22,
                    "weekly_frequency": 8.5,
                    "recency_score": 0.95,
                    "consistency_score": 0.85
                },
                "trend_information": {
                    "trend_direction": "growing",
                    "growth_rate": 0.15,
                    "momentum_score": 0.8,
                    "volatility_score": 0.2,
                    "prediction_confidence": 0.85,
                    "expected_trajectory": "continued growth"
                },
                "importance_score": 0.9,
                "confidence_score": 0.88,
                "stability_score": 0.85,
                "evidence_references": ["evidence_001", "evidence_002"],
                "supporting_event_ids": ["evt_1", "evt_2"],
                "supporting_cluster_ids": ["cluster_1"],
                "evolution_history": [],
                "version": 1,
                "created_at": "2026-05-01T00:00:00Z",
                "updated_at": "2026-06-11T00:00:00Z",
                "metadata": {},
                "tags": ["learning", "technical", "high_engagement"]
            }
        }
    
    def add_evolution_snapshot(self, notable_change: Optional[str] = None):
        """
        Add current state to evolution history
        
        Args:
            notable_change: Description of notable change
        """
        snapshot = EvolutionSnapshot(
            timestamp=datetime.utcnow(),
            occurrence_count=self.temporal_statistics.occurrence_count,
            engagement_rate=self.engagement_statistics.overall_engagement_rate,
            avg_watch_time=self.watch_statistics.avg_watch_time,
            confidence=self.confidence_score,
            notable_change=notable_change
        )
        self.evolution_history.append(snapshot)
        
        # Keep only last 30 snapshots
        if len(self.evolution_history) > 30:
            self.evolution_history = self.evolution_history[-30:]
    
    def update_version(self):
        """Increment version and update timestamp"""
        self.version += 1
        self.updated_at = datetime.utcnow()
    
    def record_access(self):
        """Record that this behavior object was accessed"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def get_age_days(self) -> int:
        """Get age of behavior in days"""
        return (datetime.now(timezone.utc) - _ensure_aware(self.created_at)).days

    def get_recency_days(self) -> int:
        """Get days since last occurrence"""
        # temporal_statistics.last_seen is timezone-aware for objects created
        # after the timestamp-normalization fix, but naive for anything
        # persisted before it — a permanently mixed dataset, so coerce
        # defensively rather than assume either format.
        return (datetime.now(timezone.utc) - _ensure_aware(self.temporal_statistics.last_seen)).days
    
    def is_active(self, days_threshold: int = 7) -> bool:
        """
        Check if behavior is currently active
        
        Args:
            days_threshold: Days since last seen to consider active
            
        Returns:
            True if active
        """
        return self.get_recency_days() <= days_threshold
    
    def is_emerging(self) -> bool:
        """Check if this is an emerging behavior"""
        return (
            self.trend_information.trend_direction == TrendDirection.EMERGING and
            self.get_age_days() <= 14 and
            self.trend_information.growth_rate > 0.5
        )
    
    def is_stable(self) -> bool:
        """Check if this is a stable behavior"""
        return (
            self.trend_information.trend_direction == TrendDirection.STABLE and
            self.stability_score > 0.7 and
            self.get_age_days() > 14
        )
    
    def is_declining(self) -> bool:
        """Check if this is a declining behavior"""
        return (
            self.trend_information.trend_direction == TrendDirection.DECLINING and
            self.trend_information.growth_rate < 0
        )
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of behavior
        
        Returns:
            Summary string
        """
        return (
            f"{self.topic}: {self.temporal_statistics.occurrence_count} occurrences, "
            f"{self.engagement_statistics.overall_engagement_rate:.1%} engagement, "
            f"{self.trend_information.trend_direction.value} trend, "
            f"confidence {self.confidence_score:.1%}"
        )
