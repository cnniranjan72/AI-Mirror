"""
Reflection Memory Module
Stores daily, weekly, and monthly summaries and system reflections
"""
from typing import List, Optional, Dict, Any
import logging

from backend.shared.contracts import MemoryRecord, MemoryType, Reflection
from .base_memory import BaseMemory


logger = logging.getLogger(__name__)


class ReflectionMemory(BaseMemory):
    """
    Reflection Memory
    
    Stores:
    - Daily summaries
    - Weekly summaries
    - Monthly summaries
    - System reflections
    - Insights and patterns
    
    Purpose:
    Maintain periodic introspection and behavioral summaries
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize reflection memory
        
        Args:
            config: Memory configuration
        """
        super().__init__(MemoryType.REFLECTION, config)
        
        # In-memory storage (in production, use database)
        self._memory_store: Dict[str, MemoryRecord] = {}
        self._reflection_store: Dict[str, Reflection] = {}
        
        logger.info("ReflectionMemory initialized")
    
    async def store(self, memory: MemoryRecord) -> bool:
        """Store a reflection memory"""
        try:
            if memory.memory_type != MemoryType.REFLECTION:
                logger.warning(f"Attempting to store non-reflection memory in ReflectionMemory")
                return False
            
            self._memory_store[memory.memory_id] = memory
            logger.debug(f"Stored reflection memory {memory.memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing reflection memory: {str(e)}", exc_info=True)
            return False
    
    async def store_reflection(self, reflection: Reflection) -> bool:
        """
        Store a reflection
        
        Args:
            reflection: Reflection to store
            
        Returns:
            True if successful
        """
        try:
            self._reflection_store[reflection.reflection_id] = reflection
            logger.debug(f"Stored reflection {reflection.reflection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing reflection: {str(e)}", exc_info=True)
            return False
    
    async def get_recent_reflections(
        self,
        reflection_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Reflection]:
        """
        Get recent reflections
        
        Args:
            reflection_type: Filter by type (daily/weekly/monthly)
            limit: Maximum number of reflections
            
        Returns:
            List of reflections
        """
        try:
            reflections = list(self._reflection_store.values())
            
            if reflection_type:
                reflections = [r for r in reflections if r.reflection_type == reflection_type]
            
            reflections.sort(key=lambda r: r.created_at, reverse=True)
            return reflections[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent reflections: {str(e)}", exc_info=True)
            return []
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        """Retrieve reflection memories"""
        try:
            memories = list(self._memory_store.values())
            memories.sort(key=lambda m: m.timestamp, reverse=True)
            return memories[:top_k]
        except Exception as e:
            logger.error(f"Error retrieving reflection memories: {str(e)}", exc_info=True)
            return []
    
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update a reflection memory"""
        try:
            if memory_id not in self._memory_store:
                return False
            memory = self._memory_store[memory_id]
            for key, value in updates.items():
                if hasattr(memory, key):
                    setattr(memory, key, value)
            return True
        except Exception as e:
            logger.error(f"Error updating reflection memory: {str(e)}", exc_info=True)
            return False
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a reflection memory"""
        try:
            if memory_id in self._memory_store:
                del self._memory_store[memory_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting reflection memory: {str(e)}", exc_info=True)
            return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count reflection memories"""
        return len(self._memory_store)


def get_reflection_memory() -> ReflectionMemory:
    """Get singleton reflection memory instance"""
    if not hasattr(get_reflection_memory, "_instance"):
        get_reflection_memory._instance = ReflectionMemory()
    return get_reflection_memory._instance
