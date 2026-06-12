"""
Behavioral Memory Module
Stores long-term habits, topic evolution, creator affinity, and interest drift
"""
from typing import List, Optional, Dict, Any
import logging

from backend.shared.contracts import MemoryRecord, MemoryType, BehaviorCluster
from .base_memory import BaseMemory


logger = logging.getLogger(__name__)


class BehavioralMemory(BaseMemory):
    """
    Behavioral Memory
    
    Stores:
    - Long-term behavioral habits
    - Topic evolution over time
    - Creator affinity patterns
    - Interest drift
    - Behavior statistics
    - Consolidated clusters
    
    Purpose:
    Maintain high-level behavioral patterns and trends
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize behavioral memory
        
        Args:
            config: Memory configuration
        """
        super().__init__(MemoryType.BEHAVIORAL, config)
        
        # In-memory storage (in production, use database)
        self._memory_store: Dict[str, MemoryRecord] = {}
        self._cluster_store: Dict[str, BehaviorCluster] = {}
        
        logger.info("BehavioralMemory initialized")
    
    async def store(self, memory: MemoryRecord) -> bool:
        """
        Store a behavioral memory
        
        Args:
            memory: Memory record to store
            
        Returns:
            True if successful
        """
        try:
            if memory.memory_type != MemoryType.BEHAVIORAL:
                logger.warning(f"Attempting to store non-behavioral memory in BehavioralMemory")
                return False
            
            self._memory_store[memory.memory_id] = memory
            logger.debug(f"Stored behavioral memory {memory.memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing behavioral memory: {str(e)}", exc_info=True)
            return False
    
    async def store_cluster(self, cluster: BehaviorCluster) -> bool:
        """
        Store a behavior cluster
        
        Args:
            cluster: Behavior cluster to store
            
        Returns:
            True if successful
        """
        try:
            self._cluster_store[cluster.cluster_id] = cluster
            logger.debug(f"Stored behavior cluster {cluster.cluster_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing cluster: {str(e)}", exc_info=True)
            return False
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        """
        Retrieve behavioral memories
        
        Args:
            query: Query string
            top_k: Number of results
            filters: Optional filters
            
        Returns:
            List of memory records
        """
        try:
            memories = list(self._memory_store.values())
            
            # Apply filters
            if filters:
                if "tags" in filters:
                    memories = [m for m in memories if any(tag in m.tags for tag in filters["tags"])]
                if "min_importance" in filters:
                    memories = [m for m in memories if m.importance_score >= filters["min_importance"]]
            
            # Sort by importance
            memories.sort(key=lambda m: m.importance_score, reverse=True)
            
            return memories[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving behavioral memories: {str(e)}", exc_info=True)
            return []
    
    async def get_clusters(
        self,
        cluster_type: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[BehaviorCluster]:
        """
        Get behavior clusters
        
        Args:
            cluster_type: Filter by cluster type
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of behavior clusters
        """
        try:
            clusters = list(self._cluster_store.values())
            
            # Apply filters
            if cluster_type:
                clusters = [c for c in clusters if c.cluster_type == cluster_type]
            
            clusters = [c for c in clusters if c.confidence >= min_confidence]
            
            # Sort by confidence
            clusters.sort(key=lambda c: c.confidence, reverse=True)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error getting clusters: {str(e)}", exc_info=True)
            return []
    
    async def get_topic_evolution(
        self,
        topic: str
    ) -> Optional[BehaviorCluster]:
        """
        Get evolution of a specific topic
        
        Args:
            topic: Topic to track
            
        Returns:
            Behavior cluster for topic
        """
        try:
            for cluster in self._cluster_store.values():
                if cluster.cluster_type == "topic" and cluster.primary_topic == topic:
                    return cluster
            return None
            
        except Exception as e:
            logger.error(f"Error getting topic evolution: {str(e)}", exc_info=True)
            return None
    
    async def get_creator_affinity(
        self,
        creator: str
    ) -> Optional[BehaviorCluster]:
        """
        Get affinity for a specific creator
        
        Args:
            creator: Creator username
            
        Returns:
            Behavior cluster for creator
        """
        try:
            for cluster in self._cluster_store.values():
                if cluster.cluster_type == "creator" and creator in cluster.creators:
                    return cluster
            return None
            
        except Exception as e:
            logger.error(f"Error getting creator affinity: {str(e)}", exc_info=True)
            return None
    
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a behavioral memory
        
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
            
            logger.debug(f"Updated behavioral memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating behavioral memory: {str(e)}", exc_info=True)
            return False
    
    async def delete(self, memory_id: str) -> bool:
        """
        Delete a behavioral memory
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if successful
        """
        try:
            if memory_id in self._memory_store:
                del self._memory_store[memory_id]
                logger.debug(f"Deleted behavioral memory {memory_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting behavioral memory: {str(e)}", exc_info=True)
            return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count behavioral memories
        
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
            logger.error(f"Error counting behavioral memories: {str(e)}", exc_info=True)
            return 0


def get_behavioral_memory() -> BehavioralMemory:
    """Get singleton behavioral memory instance"""
    if not hasattr(get_behavioral_memory, "_instance"):
        get_behavioral_memory._instance = BehavioralMemory()
    return get_behavioral_memory._instance
