"""
Character State
Computed dynamically - NEVER persisted to database
Generated fresh for every request
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from backend.identity.identity_snapshot import IdentitySnapshot
from backend.identity.self_model import SelfModel, Belief
from backend.reasoning import BehaviorObject, Inference
from backend.reasoning.reasoning_context import (
    ReasoningContext,
    MemoryReference,
    GoalReference,
    ReflectionReference
)


logger = logging.getLogger(__name__)


class PersistentState(BaseModel):
    """
    Persistent State Components
    
    Derived from stored data:
    - Identity Snapshot
    - Self Model
    - Memories
    - Goals
    """
    # Identity
    identity_snapshot_id: str = Field(..., description="Identity snapshot ID")
    identity_version: int = Field(..., description="Identity version")
    dominant_topics: List[str] = Field(default_factory=list, description="Dominant topics")
    emerging_topics: List[str] = Field(default_factory=list, description="Emerging topics")
    declining_topics: List[str] = Field(default_factory=list, description="Declining topics")
    
    # Confidence
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    identity_completeness: float = Field(..., ge=0.0, le=1.0, description="Identity completeness")
    
    # Motivation
    primary_motivation: str = Field(..., description="Primary motivation type")
    learning_motivation: float = Field(..., ge=0.0, le=1.0, description="Learning motivation")
    entertainment_seeking: float = Field(..., ge=0.0, le=1.0, description="Entertainment seeking")
    
    # Beliefs
    strong_beliefs: List[str] = Field(default_factory=list, description="Strong belief IDs")
    uncertain_beliefs: List[str] = Field(default_factory=list, description="Uncertain belief IDs")
    active_beliefs: List[Belief] = Field(default_factory=list, description="Active beliefs")
    
    # Goals
    active_goals: List[GoalReference] = Field(default_factory=list, description="Active goals")
    
    # Behavior
    active_behavior_objects: List[str] = Field(default_factory=list, description="Active behavior object IDs")
    
    # Memory counts
    behavior_memory_count: int = Field(default=0, description="Behavior memory count")
    reflection_memory_count: int = Field(default=0, description="Reflection memory count")
    goal_memory_count: int = Field(default=0, description="Goal memory count")


class EphemeralState(BaseModel):
    """
    Ephemeral State Components
    
    Runtime-specific:
    - Current conversation
    - Current query
    - Recent retrievals
    - Active inferences
    """
    # Current context
    current_timestamp: datetime = Field(..., description="Current timestamp")
    current_query: Optional[str] = Field(None, description="Current user query")
    conversation_id: Optional[str] = Field(None, description="Current conversation ID")
    
    # Recent activity
    recent_reflections: List[ReflectionReference] = Field(default_factory=list, description="Recent reflections")
    recent_retrievals: List[MemoryReference] = Field(default_factory=list, description="Recent memory retrievals")
    active_inferences: List[Inference] = Field(default_factory=list, description="Active inferences")
    
    # Current focus
    current_focus_topics: List[str] = Field(default_factory=list, description="Current focus topics")
    current_focus_confidence: float = Field(..., ge=0.0, le=1.0, description="Focus confidence")
    
    # Runtime metadata
    session_id: Optional[str] = Field(None, description="Session identifier")
    request_id: Optional[str] = Field(None, description="Request identifier")
    
    # Temporal context
    time_of_day: str = Field(..., description="Time of day")
    day_of_week: str = Field(..., description="Day of week")
    is_weekend: bool = Field(..., description="Whether it's weekend")


class CharacterState(BaseModel):
    """
    Character State - Computed Dynamically
    
    CRITICAL: This is NEVER persisted to database.
    Generated fresh for every request.
    
    Like Redux/React state - transient runtime state.
    
    Combines:
    - Persistent state (from Identity/SelfModel/Memories)
    - Ephemeral state (from current request/conversation)
    
    Every request builds a new CharacterState.
    """
    # State identification
    state_id: str = Field(..., description="Unique state identifier (ephemeral)")
    user_id: str = Field(..., description="User identifier")
    
    # Components
    persistent: PersistentState = Field(..., description="Persistent state")
    ephemeral: EphemeralState = Field(..., description="Ephemeral state")
    
    # Reasoning context
    reasoning_context: Optional[ReasoningContext] = Field(None, description="Current reasoning context")
    
    # State metadata
    generated_at: datetime = Field(..., description="When state was generated")
    ttl_seconds: int = Field(default=300, description="State TTL in seconds")
    
    # Runtime flags
    is_valid: bool = Field(default=True, description="Whether state is valid")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        arbitrary_types_allowed = True
    
    def get_age_seconds(self) -> float:
        """Get state age in seconds"""
        return (datetime.utcnow() - self.generated_at).total_seconds()
    
    def is_expired(self) -> bool:
        """Check if state has expired"""
        return self.get_age_seconds() > self.ttl_seconds
    
    def get_dominant_topics(self, limit: int = 5) -> List[str]:
        """Get dominant topics"""
        return self.persistent.dominant_topics[:limit]
    
    def get_current_focus(self) -> List[str]:
        """Get current focus topics"""
        return self.ephemeral.current_focus_topics
    
    def get_active_beliefs(self, limit: int = 5) -> List[Belief]:
        """Get active beliefs"""
        return self.persistent.active_beliefs[:limit]
    
    def get_active_goals(self) -> List[GoalReference]:
        """Get active goals"""
        return self.persistent.active_goals
    
    def get_recent_reflections(self, limit: int = 3) -> List[ReflectionReference]:
        """Get recent reflections"""
        return self.ephemeral.recent_reflections[:limit]
    
    def get_active_inferences(self, limit: int = 5) -> List[Inference]:
        """Get active inferences"""
        return self.ephemeral.active_inferences[:limit]
    
    def has_reasoning_context(self) -> bool:
        """Check if reasoning context is available"""
        return self.reasoning_context is not None
    
    def get_overall_confidence(self) -> float:
        """Get overall confidence"""
        return self.persistent.overall_confidence
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get state summary"""
        return {
            "state_id": self.state_id,
            "user_id": self.user_id,
            "identity_version": self.persistent.identity_version,
            "dominant_topics": self.get_dominant_topics(),
            "current_focus": self.get_current_focus(),
            "overall_confidence": self.get_overall_confidence(),
            "active_beliefs": len(self.persistent.active_beliefs),
            "active_goals": len(self.persistent.active_goals),
            "active_inferences": len(self.ephemeral.active_inferences),
            "recent_reflections": len(self.ephemeral.recent_reflections),
            "has_reasoning_context": self.has_reasoning_context(),
            "age_seconds": self.get_age_seconds(),
            "is_expired": self.is_expired(),
            "is_valid": self.is_valid
        }


class CharacterStateBuilder:
    """
    Character State Builder
    
    Responsibilities:
    - Build CharacterState from components
    - Compute persistent state from Identity/SelfModel
    - Compute ephemeral state from request context
    - Validate state
    
    NEVER persists state to database.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize builder
        
        Args:
            config: Builder configuration
        """
        self.config = config or {}
        self.default_ttl = self.config.get("default_ttl_seconds", 300)
        
        logger.info("CharacterStateBuilder initialized")
    
    def build_state(
        self,
        user_id: str,
        identity_snapshot: IdentitySnapshot,
        self_model: SelfModel,
        behavior_memory_ids: Optional[List[str]] = None,
        reflection_memory_ids: Optional[List[str]] = None,
        goal_memory_ids: Optional[List[str]] = None,
        active_goals: Optional[List[GoalReference]] = None,
        current_query: Optional[str] = None,
        conversation_id: Optional[str] = None,
        recent_reflections: Optional[List[ReflectionReference]] = None,
        recent_retrievals: Optional[List[MemoryReference]] = None,
        active_inferences: Optional[List[Inference]] = None,
        reasoning_context: Optional[ReasoningContext] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> CharacterState:
        """
        Build CharacterState from components
        
        Args:
            user_id: User identifier
            identity_snapshot: Identity snapshot
            self_model: Self model
            behavior_memory_ids: Behavior memory IDs
            reflection_memory_ids: Reflection memory IDs
            goal_memory_ids: Goal memory IDs
            active_goals: Active goals
            current_query: Current user query
            conversation_id: Conversation ID
            recent_reflections: Recent reflections
            recent_retrievals: Recent retrievals
            active_inferences: Active inferences
            reasoning_context: Reasoning context
            session_id: Session ID
            request_id: Request ID
            
        Returns:
            CharacterState
        """
        try:
            import uuid
            
            # Build persistent state
            persistent = self._build_persistent_state(
                identity_snapshot,
                self_model,
                behavior_memory_ids or [],
                reflection_memory_ids or [],
                goal_memory_ids or [],
                active_goals or []
            )
            
            # Build ephemeral state
            ephemeral = self._build_ephemeral_state(
                current_query,
                conversation_id,
                recent_reflections or [],
                recent_retrievals or [],
                active_inferences or [],
                session_id,
                request_id
            )
            
            # Create state
            state = CharacterState(
                state_id=f"state_{user_id}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                persistent=persistent,
                ephemeral=ephemeral,
                reasoning_context=reasoning_context,
                generated_at=datetime.utcnow(),
                ttl_seconds=self.default_ttl,
                is_valid=True,
                metadata={
                    "builder_version": "1.0",
                    "snapshot_version": identity_snapshot.identity_version
                }
            )
            
            logger.info(f"Built CharacterState {state.state_id} for user {user_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error building CharacterState: {str(e)}", exc_info=True)
            raise
    
    def _build_persistent_state(
        self,
        identity_snapshot: IdentitySnapshot,
        self_model: SelfModel,
        behavior_memory_ids: List[str],
        reflection_memory_ids: List[str],
        goal_memory_ids: List[str],
        active_goals: List[GoalReference]
    ) -> PersistentState:
        """Build persistent state from identity and self model"""
        try:
            # Get active beliefs
            active_beliefs = self_model.get_strong_beliefs()
            
            persistent = PersistentState(
                identity_snapshot_id=identity_snapshot.snapshot_id,
                identity_version=identity_snapshot.identity_version,
                dominant_topics=identity_snapshot.dominant_topics,
                emerging_topics=identity_snapshot.emerging_topics,
                declining_topics=identity_snapshot.declining_topics,
                overall_confidence=identity_snapshot.overall_confidence,
                identity_completeness=identity_snapshot.identity_completeness,
                primary_motivation=identity_snapshot.get_primary_motivation(),
                learning_motivation=identity_snapshot.motivation_signals.learning_motivation,
                entertainment_seeking=identity_snapshot.motivation_signals.entertainment_seeking,
                strong_beliefs=self_model.strong_beliefs,
                uncertain_beliefs=self_model.uncertain_beliefs,
                active_beliefs=active_beliefs,
                active_goals=active_goals,
                active_behavior_objects=[],  # Would be populated from memory
                behavior_memory_count=len(behavior_memory_ids),
                reflection_memory_count=len(reflection_memory_ids),
                goal_memory_count=len(goal_memory_ids)
            )
            
            return persistent
            
        except Exception as e:
            logger.error(f"Error building persistent state: {str(e)}", exc_info=True)
            raise
    
    def _build_ephemeral_state(
        self,
        current_query: Optional[str],
        conversation_id: Optional[str],
        recent_reflections: List[ReflectionReference],
        recent_retrievals: List[MemoryReference],
        active_inferences: List[Inference],
        session_id: Optional[str],
        request_id: Optional[str]
    ) -> EphemeralState:
        """Build ephemeral state from request context"""
        try:
            now = datetime.utcnow()
            
            # Determine time of day
            hour = now.hour
            if 5 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 17:
                time_of_day = "afternoon"
            elif 17 <= hour < 21:
                time_of_day = "evening"
            else:
                time_of_day = "night"
            
            # Determine day of week
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_of_week = day_names[now.weekday()]
            is_weekend = now.weekday() >= 5
            
            # Extract focus topics from inferences
            focus_topics = []
            for inference in active_inferences[:3]:
                focus_topics.extend(inference.affected_topics[:2])
            focus_topics = list(set(focus_topics))[:5]
            
            # Calculate focus confidence
            focus_confidence = 0.8 if active_inferences else 0.5
            
            ephemeral = EphemeralState(
                current_timestamp=now,
                current_query=current_query,
                conversation_id=conversation_id,
                recent_reflections=recent_reflections,
                recent_retrievals=recent_retrievals,
                active_inferences=active_inferences,
                current_focus_topics=focus_topics,
                current_focus_confidence=focus_confidence,
                session_id=session_id,
                request_id=request_id,
                time_of_day=time_of_day,
                day_of_week=day_of_week,
                is_weekend=is_weekend
            )
            
            return ephemeral
            
        except Exception as e:
            logger.error(f"Error building ephemeral state: {str(e)}", exc_info=True)
            raise


def get_character_state_builder() -> CharacterStateBuilder:
    """Get singleton character state builder instance"""
    if not hasattr(get_character_state_builder, "_instance"):
        get_character_state_builder._instance = CharacterStateBuilder()
    return get_character_state_builder._instance
