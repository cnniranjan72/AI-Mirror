"""
Goal Memory Module
Stores user goals, goal alignment, and progress tracking
"""
from typing import List, Optional, Dict, Any
import logging

from backend.shared.contracts import MemoryRecord, MemoryType, GoalState, GoalStatus
from .base_memory import BaseMemory


logger = logging.getLogger(__name__)


class GoalMemory(BaseMemory):
    """
    Goal Memory
    
    Stores:
    - User goals
    - Goal alignment with behavior
    - Progress tracking
    - Milestones
    
    Purpose:
    Track user goals and measure behavioral alignment
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize goal memory
        
        Args:
            config: Memory configuration
        """
        super().__init__(MemoryType.GOAL, config)
        
        # In-memory storage (in production, use database)
        self._memory_store: Dict[str, MemoryRecord] = {}
        self._goal_store: Dict[str, GoalState] = {}
        
        logger.info("GoalMemory initialized")
    
    async def store(self, memory: MemoryRecord) -> bool:
        """Store a goal memory"""
        try:
            if memory.memory_type != MemoryType.GOAL:
                logger.warning(f"Attempting to store non-goal memory in GoalMemory")
                return False
            
            self._memory_store[memory.memory_id] = memory
            logger.debug(f"Stored goal memory {memory.memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing goal memory: {str(e)}", exc_info=True)
            return False
    
    async def store_goal(self, goal: GoalState) -> bool:
        """
        Store a goal state
        
        Args:
            goal: Goal state to store
            
        Returns:
            True if successful
        """
        try:
            self._goal_store[goal.goal_id] = goal
            logger.debug(f"Stored goal {goal.goal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing goal: {str(e)}", exc_info=True)
            return False
    
    async def get_active_goals(self) -> List[GoalState]:
        """Get all active goals"""
        try:
            goals = [g for g in self._goal_store.values() if g.status == GoalStatus.ACTIVE]
            goals.sort(key=lambda g: g.progress, reverse=True)
            return goals
        except Exception as e:
            logger.error(f"Error getting active goals: {str(e)}", exc_info=True)
            return []
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        """Retrieve goal memories"""
        try:
            memories = list(self._memory_store.values())
            memories.sort(key=lambda m: m.importance_score, reverse=True)
            return memories[:top_k]
        except Exception as e:
            logger.error(f"Error retrieving goal memories: {str(e)}", exc_info=True)
            return []
    
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update a goal memory"""
        try:
            if memory_id not in self._memory_store:
                return False
            memory = self._memory_store[memory_id]
            for key, value in updates.items():
                if hasattr(memory, key):
                    setattr(memory, key, value)
            return True
        except Exception as e:
            logger.error(f"Error updating goal memory: {str(e)}", exc_info=True)
            return False
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a goal memory"""
        try:
            if memory_id in self._memory_store:
                del self._memory_store[memory_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting goal memory: {str(e)}", exc_info=True)
            return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count goal memories"""
        return len(self._memory_store)


def get_goal_memory() -> GoalMemory:
    """Get singleton goal memory instance"""
    if not hasattr(get_goal_memory, "_instance"):
        get_goal_memory._instance = GoalMemory()
    return get_goal_memory._instance
