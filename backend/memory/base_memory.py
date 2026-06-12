"""
Base Memory Interface
Defines contract for all memory modules
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging

from backend.shared.contracts import MemoryRecord, MemoryType


logger = logging.getLogger(__name__)


class BaseMemory(ABC):
    """
    Abstract base class for memory modules
    
    All memory modules must implement this interface
    """
    
    def __init__(self, memory_type: MemoryType, config: Optional[Dict[str, Any]] = None):
        """
        Initialize memory module
        
        Args:
            memory_type: Type of memory
            config: Memory-specific configuration
        """
        self.memory_type = memory_type
        self.config = config or {}
        self.module_name = self.__class__.__name__
        logger.info(f"Initializing {self.module_name}")
    
    @abstractmethod
    async def store(self, memory: MemoryRecord) -> bool:
        """
        Store a memory record
        
        Args:
            memory: Memory record to store
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        """
        Retrieve memory records
        
        Args:
            query: Query string
            top_k: Number of results to return
            filters: Optional filters
            
        Returns:
            List of memory records
        """
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a memory record
        
        Args:
            memory_id: Memory ID to update
            updates: Fields to update
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """
        Delete a memory record
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count memory records
        
        Args:
            filters: Optional filters
            
        Returns:
            Number of records
        """
        pass
    
    async def cleanup_expired(self) -> int:
        """
        Cleanup expired memories
        
        Returns:
            Number of memories deleted
        """
        # Base implementation - override in subclasses if needed
        logger.info(f"Cleaning up expired memories in {self.module_name}")
        return 0
    
    def get_memory_type(self) -> MemoryType:
        """
        Get memory type
        
        Returns:
            Memory type
        """
        return self.memory_type
