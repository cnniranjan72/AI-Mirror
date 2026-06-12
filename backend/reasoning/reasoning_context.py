"""
Reasoning Context
Bundles all contextual information for cognitive reasoning
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .behavior_object import BehaviorObject
from .evidence_engine import Evidence


class TemporalContext(BaseModel):
    """Temporal context for reasoning"""
    current_time: datetime = Field(..., description="Current timestamp")
    time_window_start: datetime = Field(..., description="Start of analysis window")
    time_window_end: datetime = Field(..., description="End of analysis window")
    time_of_day: str = Field(..., description="Time of day (morning/afternoon/evening/night)")
    day_of_week: str = Field(..., description="Day of week")
    is_weekend: bool = Field(..., description="Whether it's weekend")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_time": "2026-06-12T00:30:00Z",
                "time_window_start": "2026-05-12T00:00:00Z",
                "time_window_end": "2026-06-12T00:00:00Z",
                "time_of_day": "night",
                "day_of_week": "Wednesday",
                "is_weekend": False
            }
        }


class MemoryReference(BaseModel):
    """Reference to a memory object"""
    memory_id: str = Field(..., description="Memory identifier")
    memory_type: str = Field(..., description="Type of memory (episodic/semantic/behavioral/goal/reflection)")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to current reasoning")
    summary: Optional[str] = Field(None, description="Brief summary of memory")
    
    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "memory_episodic_001",
                "memory_type": "episodic",
                "relevance_score": 0.85,
                "summary": "User watched AI tutorial on June 10"
            }
        }


class GoalReference(BaseModel):
    """Reference to a goal"""
    goal_id: str = Field(..., description="Goal identifier")
    goal_description: str = Field(..., description="Goal description")
    goal_status: str = Field(..., description="Goal status (active/completed/abandoned)")
    progress: float = Field(..., ge=0.0, le=1.0, description="Goal progress")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to current reasoning")
    
    class Config:
        json_schema_extra = {
            "example": {
                "goal_id": "goal_001",
                "goal_description": "Learn machine learning fundamentals",
                "goal_status": "active",
                "progress": 0.6,
                "relevance_score": 0.9
            }
        }


class ReflectionReference(BaseModel):
    """Reference to a reflection"""
    reflection_id: str = Field(..., description="Reflection identifier")
    reflection_type: str = Field(..., description="Type of reflection (daily/weekly/monthly)")
    reflection_date: datetime = Field(..., description="When reflection was created")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from reflection")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to current reasoning")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reflection_id": "reflection_daily_20260611",
                "reflection_type": "daily",
                "reflection_date": "2026-06-11T23:59:59Z",
                "key_insights": ["Increased focus on AI learning", "High engagement with tutorials"],
                "relevance_score": 0.95
            }
        }


class ReasoningContext(BaseModel):
    """
    Reasoning Context
    
    Bundles all contextual information needed for cognitive reasoning.
    This object is passed to the Inference Engine and all reasoning components.
    
    Purpose:
    - Provide complete context for behavioral interpretation
    - Enable evidence-based reasoning
    - Support goal-aware decision making
    - Facilitate temporal reasoning
    - Enable memory-aware inference
    """
    # Core context
    context_id: str = Field(..., description="Unique context identifier")
    created_at: datetime = Field(..., description="When context was created")
    
    # Behavioral data
    behavior_objects: List[BehaviorObject] = Field(default_factory=list, description="Relevant behavior objects")
    primary_behaviors: List[str] = Field(default_factory=list, description="IDs of primary behaviors")
    emerging_behaviors: List[str] = Field(default_factory=list, description="IDs of emerging behaviors")
    declining_behaviors: List[str] = Field(default_factory=list, description="IDs of declining behaviors")
    
    # Evidence
    evidence: List[Evidence] = Field(default_factory=list, description="Supporting evidence")
    evidence_summary: Optional[str] = Field(None, description="Summary of evidence")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in context")
    
    # Memory references
    memory_references: List[MemoryReference] = Field(default_factory=list, description="Relevant memory references")
    episodic_memories: List[str] = Field(default_factory=list, description="IDs of relevant episodic memories")
    semantic_memories: List[str] = Field(default_factory=list, description="IDs of relevant semantic memories")
    
    # Goals
    goal_references: List[GoalReference] = Field(default_factory=list, description="Relevant goals")
    active_goals: List[str] = Field(default_factory=list, description="IDs of active goals")
    
    # Reflections
    reflection_references: List[ReflectionReference] = Field(default_factory=list, description="Relevant reflections")
    recent_reflections: List[str] = Field(default_factory=list, description="IDs of recent reflections")
    
    # Temporal context
    temporal_context: TemporalContext = Field(..., description="Temporal context")
    
    # User context
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Current session identifier")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Context tags")
    
    class Config:
        json_schema_extra = {
            "example": {
                "context_id": "context_20260612_001",
                "created_at": "2026-06-12T00:30:00Z",
                "behavior_objects": [],
                "primary_behaviors": ["behavior_ai_learning", "behavior_tech_tutorials"],
                "emerging_behaviors": ["behavior_ml_fundamentals"],
                "declining_behaviors": ["behavior_entertainment"],
                "evidence": [],
                "evidence_summary": "Strong evidence of learning motivation",
                "overall_confidence": 0.85,
                "memory_references": [],
                "episodic_memories": ["memory_001", "memory_002"],
                "semantic_memories": ["semantic_001"],
                "goal_references": [],
                "active_goals": ["goal_001"],
                "reflection_references": [],
                "recent_reflections": ["reflection_daily_20260611"],
                "temporal_context": {
                    "current_time": "2026-06-12T00:30:00Z",
                    "time_window_start": "2026-05-12T00:00:00Z",
                    "time_window_end": "2026-06-12T00:00:00Z",
                    "time_of_day": "night",
                    "day_of_week": "Wednesday",
                    "is_weekend": False
                },
                "user_id": "user_001",
                "session_id": "session_123",
                "metadata": {},
                "tags": ["learning_focused", "high_engagement"]
            }
        }
    
    def add_behavior_object(self, behavior: BehaviorObject):
        """
        Add a behavior object to context
        
        Args:
            behavior: BehaviorObject to add
        """
        self.behavior_objects.append(behavior)
        
        # Categorize by lifecycle state
        if behavior.is_emerging():
            self.emerging_behaviors.append(behavior.unique_id)
        elif behavior.is_declining():
            self.declining_behaviors.append(behavior.unique_id)
        else:
            self.primary_behaviors.append(behavior.unique_id)
    
    def add_evidence(self, evidence: Evidence):
        """
        Add evidence to context
        
        Args:
            evidence: Evidence to add
        """
        self.evidence.append(evidence)
    
    def add_memory_reference(self, memory_ref: MemoryReference):
        """
        Add memory reference to context
        
        Args:
            memory_ref: MemoryReference to add
        """
        self.memory_references.append(memory_ref)
        
        if memory_ref.memory_type == "episodic":
            self.episodic_memories.append(memory_ref.memory_id)
        elif memory_ref.memory_type == "semantic":
            self.semantic_memories.append(memory_ref.memory_id)
    
    def add_goal_reference(self, goal_ref: GoalReference):
        """
        Add goal reference to context
        
        Args:
            goal_ref: GoalReference to add
        """
        self.goal_references.append(goal_ref)
        
        if goal_ref.goal_status == "active":
            self.active_goals.append(goal_ref.goal_id)
    
    def add_reflection_reference(self, reflection_ref: ReflectionReference):
        """
        Add reflection reference to context
        
        Args:
            reflection_ref: ReflectionReference to add
        """
        self.reflection_references.append(reflection_ref)
        self.recent_reflections.append(reflection_ref.reflection_id)
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of context
        
        Returns:
            Summary string
        """
        return (
            f"ReasoningContext for {self.user_id}: "
            f"{len(self.behavior_objects)} behaviors, "
            f"{len(self.evidence)} evidence pieces, "
            f"{len(self.goal_references)} goals, "
            f"{len(self.reflection_references)} reflections, "
            f"confidence {self.overall_confidence:.1%}"
        )
    
    def get_primary_topics(self, limit: int = 5) -> List[str]:
        """
        Get primary topics from behavior objects
        
        Args:
            limit: Maximum number of topics
            
        Returns:
            List of topic names
        """
        topics = [b.topic for b in self.behavior_objects if b.unique_id in self.primary_behaviors]
        return topics[:limit]
    
    def get_emerging_topics(self, limit: int = 3) -> List[str]:
        """
        Get emerging topics from behavior objects
        
        Args:
            limit: Maximum number of topics
            
        Returns:
            List of topic names
        """
        topics = [b.topic for b in self.behavior_objects if b.unique_id in self.emerging_behaviors]
        return topics[:limit]
    
    def has_sufficient_evidence(self, min_evidence: int = 2) -> bool:
        """
        Check if context has sufficient evidence
        
        Args:
            min_evidence: Minimum evidence count
            
        Returns:
            True if sufficient evidence
        """
        return len(self.evidence) >= min_evidence
    
    def is_goal_aligned(self) -> bool:
        """
        Check if behaviors align with active goals
        
        Returns:
            True if goal-aligned
        """
        return len(self.active_goals) > 0 and len(self.primary_behaviors) > 0
