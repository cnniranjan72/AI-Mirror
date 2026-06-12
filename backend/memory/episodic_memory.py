"""
Episodic Memory Module
Stores individual events, timestamps, and watch sessions
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from backend.shared.contracts import MemoryRecord, MemoryType
from .base_memory import BaseMemory


logger = logging.getLogger(__name__)


class EpisodicMemory(BaseMemory):
    """
    Episodic Memory
    
    Stores:
    - Individual behavioral events
    - Timestamps
    - Watch sessions
    - Contextual information
    
    Purpose:
    Maintain a chronological record of user's behavioral history
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize episodic memory
        
        Args:
            config: Memory configuration
        """
        super().__init__(MemoryType.EPISODIC, config)
        
        # In-memory storage (in production, use database)
        self._memory_store: Dict[str, MemoryRecord] = {}
        
        logger.info("EpisodicMemory initialized")
    
    async def store(self, memory: MemoryRecord) -> bool:
        """
        Store an episodic memory
        
        Args:
            memory: Memory record to store
            
        Returns:
            True if successful
        """
        try:
            if memory.memory_type != MemoryType.EPISODIC:
                logger.warning(f"Attempting to store non-episodic memory in EpisodicMemory")
                return False
            
            self._memory_store[memory.memory_id] = memory
            logger.debug(f"Stored episodic memory {memory.memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing episodic memory: {str(e)}", exc_info=True)
            return False
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        """
        Retrieve episodic memories
        
        Args:
            query: Query string
            top_k: Number of results
            filters: Optional filters (e.g., time range)
            
        Returns:
            List of memory records
        """
        try:
            # Simple retrieval (in production, use vector search)
            memories = list(self._memory_store.values())
            
            # Apply filters
            if filters:
                if "start_time" in filters:
                    memories = [m for m in memories if m.timestamp >= filters["start_time"]]
                if "end_time" in filters:
                    memories = [m for m in memories if m.timestamp <= filters["end_time"]]
                if "tags" in filters:
                    memories = [m for m in memories if any(tag in m.tags for tag in filters["tags"])]
            
            # Sort by timestamp (most recent first)
            memories.sort(key=lambda m: m.timestamp, reverse=True)
            
            return memories[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving episodic memories: {str(e)}", exc_info=True)
            return []
    
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an episodic memory
        
        Args:
            memory_id: Memory ID
            updates: Fields to update
            
        Returns:
            True if successful
        """
        try:
            if memory_id not in self._memory_store:
                logger.warning(f"Memory {memory_id} not found")
                return False
            
            memory = self._memory_store[memory_id]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(memory, key):
                    setattr(memory, key, value)
            
            # Update access count
            memory.access_count += 1
            memory.last_accessed = datetime.utcnow()
            
            logger.debug(f"Updated episodic memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating episodic memory: {str(e)}", exc_info=True)
            return False
    
    async def delete(self, memory_id: str) -> bool:
        """
        Delete an episodic memory
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if successful
        """
        try:
            if memory_id in self._memory_store:
                del self._memory_store[memory_id]
                logger.debug(f"Deleted episodic memory {memory_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting episodic memory: {str(e)}", exc_info=True)
            return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count episodic memories
        
        Args:
            filters: Optional filters
            
        Returns:
            Number of records
        """
        try:
            if not filters:
                return len(self._memory_store)
            
            # Apply filters
            memories = list(self._memory_store.values())
            if "start_time" in filters:
                memories = [m for m in memories if m.timestamp >= filters["start_time"]]
            if "end_time" in filters:
                memories = [m for m in memories if m.timestamp <= filters["end_time"]]
            
            return len(memories)
            
        except Exception as e:
            logger.error(f"Error counting episodic memories: {str(e)}", exc_info=True)
            return 0
    
    async def get_session_memories(
        self,
        session_id: str
    ) -> List[MemoryRecord]:
        """
        Get all memories for a specific session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of memory records
        """
        try:
            memories = [
                m for m in self._memory_store.values()
                if m.context.get("session_id") == session_id
            ]
            memories.sort(key=lambda m: m.timestamp)
            return memories
            
        except Exception as e:
            logger.error(f"Error getting session memories: {str(e)}", exc_info=True)
            return []
    
    async def get_timeline(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[MemoryRecord]:
        """
        Get chronological timeline of memories
        
        Args:
            start_time: Start of timeline
            end_time: End of timeline
            
        Returns:
            List of memory records in chronological order
        """
        try:
            memories = [
                m for m in self._memory_store.values()
                if start_time <= m.timestamp <= end_time
            ]
            memories.sort(key=lambda m: m.timestamp)
            return memories
            
        except Exception as e:
            logger.error(f"Error getting timeline: {str(e)}", exc_info=True)
            return []


def get_episodic_memory() -> EpisodicMemory:
    """Get singleton episodic memory instance"""
    if not hasattr(get_episodic_memory, "_instance"):
        get_episodic_memory._instance = EpisodicMemory()
    return get_episodic_memory._instance
