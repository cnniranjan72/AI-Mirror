"""
Character Core
Orchestration kernel for character runtime
NO business logic - only coordination
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from backend.identity.identity_snapshot import IdentitySnapshot
from backend.identity.self_model import SelfModel
from backend.reasoning import Inference
from backend.reasoning.reasoning_context import (
    ReasoningContext,
    MemoryReference,
    GoalReference,
    ReflectionReference
)


logger = logging.getLogger(__name__)


class CharacterCore(BaseModel):
    """
    Character Core - Orchestration Kernel
    
    Purpose:
    - Coordinate cognitive components
    - Provide unified access to identity, beliefs, memories
    - Enable multiple character implementations
    - NO business logic
    
    CharacterCore is the kernel.
    VirtualCharacter, CoachCharacter, MentorCharacter are interfaces.
    All share the same CharacterCore.
    
    Like Linux Kernel vs Ubuntu/Fedora/Arch.
    """
    # Core identification
    core_id: str = Field(..., description="Unique core identifier")
    user_id: str = Field(..., description="User identifier")
    
    # Identity (immutable snapshot)
    identity_snapshot: IdentitySnapshot = Field(..., description="Identity snapshot")
    
    # Beliefs
    self_model: SelfModel = Field(..., description="Self model with beliefs")
    
    # Memory references (IDs only - no data loading here)
    behavior_memory_ids: List[str] = Field(default_factory=list, description="Behavior memory IDs")
    reflection_memory_ids: List[str] = Field(default_factory=list, description="Reflection memory IDs")
    goal_memory_ids: List[str] = Field(default_factory=list, description="Goal memory IDs")
    episodic_memory_ids: List[str] = Field(default_factory=list, description="Episodic memory IDs")
    semantic_memory_ids: List[str] = Field(default_factory=list, description="Semantic memory IDs")
    
    # Reasoning context
    reasoning_context: Optional[ReasoningContext] = Field(None, description="Current reasoning context")
    
    # Inference history (recent inferences)
    inference_history: List[Inference] = Field(default_factory=list, description="Recent inferences")
    
    # Runtime metadata
    created_at: datetime = Field(..., description="When core was created")
    last_accessed: datetime = Field(..., description="Last access timestamp")
    access_count: int = Field(default=0, description="Access count")
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Core configuration")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        arbitrary_types_allowed = True
    
    def update_access(self):
        """Update access tracking"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
    
    def get_snapshot_version(self) -> int:
        """Get identity snapshot version"""
        return self.identity_snapshot.identity_version
    
    def is_snapshot_valid(self) -> bool:
        """Check if snapshot is still valid"""
        return self.identity_snapshot.is_valid()
    
    def get_dominant_topics(self, limit: int = 5) -> List[str]:
        """Get dominant topics from snapshot"""
        return self.identity_snapshot.dominant_topics[:limit]
    
    def get_emerging_topics(self, limit: int = 3) -> List[str]:
        """Get emerging topics from snapshot"""
        return self.identity_snapshot.emerging_topics[:limit]
    
    def get_strong_beliefs(self) -> List[str]:
        """Get strong belief IDs"""
        return self.self_model.strong_beliefs
    
    def get_uncertain_beliefs(self) -> List[str]:
        """Get uncertain belief IDs"""
        return self.self_model.uncertain_beliefs
    
    def get_primary_motivation(self) -> str:
        """Get primary motivation from snapshot"""
        return self.identity_snapshot.get_primary_motivation()
    
    def get_overall_confidence(self) -> float:
        """Get overall confidence"""
        return self.identity_snapshot.overall_confidence
    
    def get_uncertainty_domains(self) -> List[str]:
        """Get high uncertainty domains"""
        return self.self_model.uncertainty_map.high_uncertainty_domains
    
    def get_memory_count(self) -> Dict[str, int]:
        """Get memory counts by type"""
        return {
            "behavior": len(self.behavior_memory_ids),
            "reflection": len(self.reflection_memory_ids),
            "goal": len(self.goal_memory_ids),
            "episodic": len(self.episodic_memory_ids),
            "semantic": len(self.semantic_memory_ids)
        }
    
    def get_inference_count(self) -> int:
        """Get inference history count"""
        return len(self.inference_history)
    
    def has_reasoning_context(self) -> bool:
        """Check if reasoning context is available"""
        return self.reasoning_context is not None
    
    def get_runtime_summary(self) -> Dict[str, Any]:
        """Get runtime summary"""
        return {
            "core_id": self.core_id,
            "user_id": self.user_id,
            "snapshot_version": self.get_snapshot_version(),
            "snapshot_valid": self.is_snapshot_valid(),
            "dominant_topics": self.get_dominant_topics(),
            "primary_motivation": self.get_primary_motivation(),
            "overall_confidence": self.get_overall_confidence(),
            "strong_beliefs": len(self.get_strong_beliefs()),
            "uncertain_beliefs": len(self.get_uncertain_beliefs()),
            "memory_counts": self.get_memory_count(),
            "inference_count": self.get_inference_count(),
            "has_reasoning_context": self.has_reasoning_context(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat()
        }


class CharacterCoreFactory:
    """
    Factory for creating CharacterCore instances
    
    Responsibilities:
    - Assemble CharacterCore from components
    - Validate components
    - Configure core
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize factory
        
        Args:
            config: Factory configuration
        """
        self.config = config or {}
        logger.info("CharacterCoreFactory initialized")
    
    def create_core(
        self,
        user_id: str,
        identity_snapshot: IdentitySnapshot,
        self_model: SelfModel,
        behavior_memory_ids: Optional[List[str]] = None,
        reflection_memory_ids: Optional[List[str]] = None,
        goal_memory_ids: Optional[List[str]] = None,
        episodic_memory_ids: Optional[List[str]] = None,
        semantic_memory_ids: Optional[List[str]] = None,
        reasoning_context: Optional[ReasoningContext] = None,
        inference_history: Optional[List[Inference]] = None,
        core_config: Optional[Dict[str, Any]] = None
    ) -> CharacterCore:
        """
        Create CharacterCore instance
        
        Args:
            user_id: User identifier
            identity_snapshot: Identity snapshot
            self_model: Self model
            behavior_memory_ids: Behavior memory IDs
            reflection_memory_ids: Reflection memory IDs
            goal_memory_ids: Goal memory IDs
            episodic_memory_ids: Episodic memory IDs
            semantic_memory_ids: Semantic memory IDs
            reasoning_context: Reasoning context
            inference_history: Recent inferences
            core_config: Core configuration
            
        Returns:
            CharacterCore instance
        """
        try:
            import uuid
            
            core = CharacterCore(
                core_id=f"core_{user_id}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                identity_snapshot=identity_snapshot,
                self_model=self_model,
                behavior_memory_ids=behavior_memory_ids or [],
                reflection_memory_ids=reflection_memory_ids or [],
                goal_memory_ids=goal_memory_ids or [],
                episodic_memory_ids=episodic_memory_ids or [],
                semantic_memory_ids=semantic_memory_ids or [],
                reasoning_context=reasoning_context,
                inference_history=inference_history or [],
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                config=core_config or {},
                metadata={
                    "factory_version": "1.0",
                    "created_by": "CharacterCoreFactory"
                }
            )
            
            logger.info(f"Created CharacterCore {core.core_id} for user {user_id}")
            return core
            
        except Exception as e:
            logger.error(f"Error creating CharacterCore: {str(e)}", exc_info=True)
            raise


def get_character_core() -> CharacterCoreFactory:
    """Get singleton character core factory instance"""
    if not hasattr(get_character_core, "_instance"):
        get_character_core._instance = CharacterCoreFactory()
    return get_character_core._instance
