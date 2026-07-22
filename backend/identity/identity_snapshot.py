"""
Identity Snapshot
Immutable snapshot of Identity for reasoning and conversation
Prevents live identity mutations during active sessions
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .identity_engine import (
    Identity,
    BehaviorProfile,
    InterestGraph,
    CreatorGraph,
    LearningStyle,
    AttentionProfile,
    ExplorationProfile,
    ConsistencyProfile,
    HabitProfile,
    MotivationSignals
)


logger = logging.getLogger(__name__)


class IdentitySnapshot(BaseModel):
    """
    Immutable Identity Snapshot
    
    Purpose:
    - Provide stable identity view during conversations
    - Prevent identity mutations mid-conversation
    - Enable versioned identity access
    - Support rollback and comparison
    
    Character reads from Snapshot, never from live Identity.
    """
    # Snapshot metadata
    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    identity_id: str = Field(..., description="Source identity ID")
    identity_version: int = Field(..., description="Identity version at snapshot time")
    snapshot_timestamp: datetime = Field(..., description="When snapshot was created")
    
    # Frozen identity data
    user_id: str = Field(..., description="User identifier")
    behavior_profile: BehaviorProfile = Field(..., description="Behavioral profile")
    interest_graph: InterestGraph = Field(..., description="Interest graph")
    creator_graph: CreatorGraph = Field(..., description="Creator affinity graph")
    learning_style: LearningStyle = Field(..., description="Learning style profile")
    attention_profile: AttentionProfile = Field(..., description="Attention profile")
    exploration_profile: ExplorationProfile = Field(..., description="Exploration profile")
    consistency_profile: ConsistencyProfile = Field(..., description="Consistency profile")
    habit_profile: HabitProfile = Field(..., description="Habit profile")
    motivation_signals: MotivationSignals = Field(..., description="Motivation signals")
    
    # Frozen topics
    dominant_topics: List[str] = Field(default_factory=list, description="Dominant topics")
    emerging_topics: List[str] = Field(default_factory=list, description="Emerging topics")
    declining_topics: List[str] = Field(default_factory=list, description="Declining topics")
    
    # Frozen preferences
    long_term_preferences: Dict[str, float] = Field(default_factory=dict, description="Long-term preferences")
    
    # Frozen confidence
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    identity_completeness: float = Field(..., ge=0.0, le=1.0, description="Identity completeness")
    
    # Snapshot validity
    valid_until: Optional[datetime] = Field(None, description="Snapshot expiration time")
    is_active: bool = Field(default=True, description="Whether snapshot is active")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        frozen = True  # Make snapshot immutable
        json_schema_extra = {
            "example": {
                "snapshot_id": "snapshot_identity_user123_v41_20260612",
                "identity_id": "identity_user123",
                "identity_version": 41,
                "snapshot_timestamp": "2026-06-12T00:50:00Z",
                "user_id": "user123",
                "overall_confidence": 0.87,
                "identity_completeness": 0.92,
                "valid_until": "2026-06-12T01:50:00Z",
                "is_active": True
            }
        }
    
    @classmethod
    def from_identity(
        cls,
        identity: Identity,
        validity_hours: int = 1
    ) -> "IdentitySnapshot":
        """
        Create snapshot from Identity
        
        Args:
            identity: Source identity
            validity_hours: Snapshot validity in hours
            
        Returns:
            IdentitySnapshot
        """
        try:
            now = datetime.utcnow()
            from datetime import timedelta
            
            snapshot = cls(
                snapshot_id=f"snapshot_{identity.identity_id}_v{identity.identity_version}_{int(now.timestamp())}",
                identity_id=identity.identity_id,
                identity_version=identity.identity_version,
                snapshot_timestamp=now,
                user_id=identity.user_id,
                behavior_profile=identity.behavior_profile,
                interest_graph=identity.interest_graph,
                creator_graph=identity.creator_graph,
                learning_style=identity.learning_style,
                attention_profile=identity.attention_profile,
                exploration_profile=identity.exploration_profile,
                consistency_profile=identity.consistency_profile,
                habit_profile=identity.habit_profile,
                motivation_signals=identity.motivation_signals,
                dominant_topics=identity.dominant_topics.copy(),
                emerging_topics=identity.emerging_topics.copy(),
                declining_topics=identity.declining_topics.copy(),
                long_term_preferences=identity.long_term_preferences.copy(),
                overall_confidence=identity.overall_confidence,
                identity_completeness=identity.identity_completeness,
                valid_until=now + timedelta(hours=validity_hours),
                is_active=True,
                metadata={
                    "source_identity_created_at": identity.created_at.isoformat(),
                    "source_identity_updated_at": identity.updated_at.isoformat(),
                    **{k: v for k, v in identity.metadata.items()
                       if k not in ("source_identity_created_at", "source_identity_updated_at")}
                }
            )
            
            logger.info(f"Created snapshot {snapshot.snapshot_id} from identity {identity.identity_id} v{identity.identity_version}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating snapshot: {str(e)}", exc_info=True)
            raise
    
    def is_valid(self) -> bool:
        """
        Check if snapshot is still valid
        
        Returns:
            True if valid
        """
        if not self.is_active:
            return False
        
        if self.valid_until is None:
            return True
        
        return datetime.utcnow() < self.valid_until
    
    def get_age_seconds(self) -> float:
        """
        Get snapshot age in seconds
        
        Returns:
            Age in seconds
        """
        return (datetime.utcnow() - self.snapshot_timestamp).total_seconds()
    
    def get_summary(self) -> str:
        """
        Get human-readable summary
        
        Returns:
            Summary string
        """
        return (
            f"IdentitySnapshot v{self.identity_version}: "
            f"{len(self.dominant_topics)} dominant topics, "
            f"{len(self.emerging_topics)} emerging, "
            f"confidence {self.overall_confidence:.1%}, "
            f"age {self.get_age_seconds():.0f}s"
        )
    
    def get_top_interests(self, limit: int = 5) -> List[str]:
        """
        Get top interests from snapshot
        
        Args:
            limit: Maximum number of interests
            
        Returns:
            List of topic names
        """
        return [node.topic for node in self.interest_graph.dominant_interests[:limit]]
    
    def get_primary_motivation(self) -> str:
        """
        Get primary motivation type
        
        Returns:
            Motivation type
        """
        signals = self.motivation_signals
        
        if signals.learning_motivation > 0.7:
            return "learning"
        elif signals.entertainment_seeking > 0.7:
            return "entertainment"
        elif signals.skill_building_intent > 0.7:
            return "skill_building"
        elif signals.curiosity_score > 0.7:
            return "exploration"
        else:
            return "mixed"


class SnapshotManager:
    """
    Manages Identity Snapshots
    
    Responsibilities:
    - Create snapshots from Identity
    - Validate snapshot freshness
    - Invalidate expired snapshots
    - Track active snapshots
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Snapshot Manager
        
        Args:
            config: Manager configuration
        """
        self.config = config or {}
        self.default_validity_hours = self.config.get("default_validity_hours", 1)
        self.max_active_snapshots = self.config.get("max_active_snapshots", 10)
        
        # In-memory snapshot cache
        self._active_snapshots: Dict[str, IdentitySnapshot] = {}
        
        logger.info("SnapshotManager initialized")
    
    def create_snapshot(
        self,
        identity: Identity,
        validity_hours: Optional[int] = None
    ) -> IdentitySnapshot:
        """
        Create snapshot from Identity
        
        Args:
            identity: Source identity
            validity_hours: Optional validity override
            
        Returns:
            IdentitySnapshot
        """
        try:
            validity = validity_hours or self.default_validity_hours
            snapshot = IdentitySnapshot.from_identity(identity, validity)
            
            # Cache snapshot
            self._active_snapshots[snapshot.snapshot_id] = snapshot
            
            # Cleanup old snapshots
            self._cleanup_expired_snapshots()
            
            logger.info(f"Created and cached snapshot {snapshot.snapshot_id}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating snapshot: {str(e)}", exc_info=True)
            raise
    
    def get_snapshot(self, snapshot_id: str) -> Optional[IdentitySnapshot]:
        """
        Get snapshot by ID
        
        Args:
            snapshot_id: Snapshot identifier
            
        Returns:
            IdentitySnapshot if found and valid, None otherwise
        """
        snapshot = self._active_snapshots.get(snapshot_id)
        
        if snapshot and snapshot.is_valid():
            return snapshot
        
        return None
    
    def invalidate_snapshot(self, snapshot_id: str):
        """
        Invalidate a snapshot
        
        Args:
            snapshot_id: Snapshot identifier
        """
        if snapshot_id in self._active_snapshots:
            del self._active_snapshots[snapshot_id]
            logger.info(f"Invalidated snapshot {snapshot_id}")
    
    def get_latest_snapshot_for_user(self, user_id: str) -> Optional[IdentitySnapshot]:
        """
        Get latest valid snapshot for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Latest IdentitySnapshot or None
        """
        user_snapshots = [
            s for s in self._active_snapshots.values()
            if s.user_id == user_id and s.is_valid()
        ]
        
        if not user_snapshots:
            return None
        
        # Sort by timestamp descending
        user_snapshots.sort(key=lambda s: s.snapshot_timestamp, reverse=True)
        return user_snapshots[0]
    
    def _cleanup_expired_snapshots(self):
        """Remove expired snapshots from cache"""
        try:
            expired_ids = [
                sid for sid, snapshot in self._active_snapshots.items()
                if not snapshot.is_valid()
            ]
            
            for sid in expired_ids:
                del self._active_snapshots[sid]
            
            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired snapshots")
            
            # Limit total snapshots
            if len(self._active_snapshots) > self.max_active_snapshots:
                # Remove oldest
                sorted_snapshots = sorted(
                    self._active_snapshots.items(),
                    key=lambda x: x[1].snapshot_timestamp
                )
                
                to_remove = len(self._active_snapshots) - self.max_active_snapshots
                for sid, _ in sorted_snapshots[:to_remove]:
                    del self._active_snapshots[sid]
                
                logger.info(f"Removed {to_remove} old snapshots to maintain limit")
                
        except Exception as e:
            logger.error(f"Error cleaning up snapshots: {str(e)}", exc_info=True)
    
    def get_active_snapshot_count(self) -> int:
        """Get count of active snapshots"""
        return len([s for s in self._active_snapshots.values() if s.is_valid()])


def get_snapshot_manager() -> SnapshotManager:
    """Get singleton snapshot manager instance"""
    if not hasattr(get_snapshot_manager, "_instance"):
        get_snapshot_manager._instance = SnapshotManager()
    return get_snapshot_manager._instance
