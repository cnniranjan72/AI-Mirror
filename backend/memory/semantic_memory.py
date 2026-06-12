"""
Semantic Memory Module
Stores embeddings, expanded content, and knowledge
"""
from typing import List, Optional, Dict, Any
import logging

from backend.shared.contracts import MemoryRecord, MemoryType
from .base_memory import BaseMemory


logger = logging.getLogger(__name__)


class SemanticMemory(BaseMemory):
    """
    Semantic Memory
    
    Stores:
    - Vector embeddings
    - Expanded content
    - Knowledge representations
    - Semantic relationships
    
    Purpose:
    Enable semantic search and retrieval based on meaning
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize semantic memory
        
        Args:
            config: Memory configuration
        """
        super().__init__(MemoryType.SEMANTIC, config)
        
        # In-memory storage (in production, use vector database)
        self._memory_store: Dict[str, MemoryRecord] = {}
        
        logger.info("SemanticMemory initialized")
    
    async def store(self, memory: MemoryRecord) -> bool:
        """
        Store a semantic memory with embedding
        
        Args:
            memory: Memory record to store
            
        Returns:
            True if successful
        """
        try:
            if memory.memory_type != MemoryType.SEMANTIC:
                logger.warning(f"Attempting to store non-semantic memory in SemanticMemory")
                return False
            
            if not memory.embedding:
                logger.warning(f"Semantic memory {memory.memory_id} has no embedding")
                return False
            
            self._memory_store[memory.memory_id] = memory
            logger.debug(f"Stored semantic memory {memory.memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing semantic memory: {str(e)}", exc_info=True)
            return False
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        """
        Retrieve semantic memories using vector similarity
        
        Args:
            query: Query string (will be embedded)
            top_k: Number of results
            filters: Optional filters
            
        Returns:
            List of memory records
        """
        try:
            # In production, use vector database for similarity search
            # For now, return all memories
            memories = list(self._memory_store.values())
            
            # Apply filters
            if filters:
                if "tags" in filters:
                    memories = [m for m in memories if any(tag in m.tags for tag in filters["tags"])]
                if "min_importance" in filters:
                    memories = [m for m in memories if m.importance_score >= filters["min_importance"]]
            
            # Sort by importance (in production, sort by similarity score)
            memories.sort(key=lambda m: m.importance_score, reverse=True)
            
            return memories[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving semantic memories: {str(e)}", exc_info=True)
            return []
    
    async def retrieve_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        """
        Retrieve semantic memories using embedding directly
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            filters: Optional filters
            
        Returns:
            List of memory records
        """
        try:
            # In production, use vector database for similarity search
            # For now, return all memories
            memories = list(self._memory_store.values())
            
            # Apply filters
            if filters:
                if "tags" in filters:
                    memories = [m for m in memories if any(tag in m.tags for tag in filters["tags"])]
            
            # Sort by importance (in production, calculate cosine similarity)
            memories.sort(key=lambda m: m.importance_score, reverse=True)
            
            return memories[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving by embedding: {str(e)}", exc_info=True)
            return []
    
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a semantic memory
        
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
            
            logger.debug(f"Updated semantic memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating semantic memory: {str(e)}", exc_info=True)
            return False
    
    async def delete(self, memory_id: str) -> bool:
        """
        Delete a semantic memory
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if successful
        """
        try:
            if memory_id in self._memory_store:
                del self._memory_store[memory_id]
                logger.debug(f"Deleted semantic memory {memory_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting semantic memory: {str(e)}", exc_info=True)
            return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count semantic memories
        
        Args:
            filters: Optional filters
            
        Returns:
            Number of records
        """
        try:
            if not filters:
                return len(self._memory_store)
            
            memories = list(self._memory_store.values())
            if "tags" in filters:
                memories = [m for m in memories if any(tag in m.tags for tag in filters["tags"])]
            
            return len(memories)
            
        except Exception as e:
            logger.error(f"Error counting semantic memories: {str(e)}", exc_info=True)
            return 0


def get_semantic_memory() -> SemanticMemory:
    """Get singleton semantic memory instance"""
    if not hasattr(get_semantic_memory, "_instance"):
        get_semantic_memory._instance = SemanticMemory()
    return get_semantic_memory._instance
