"""
Base Content Provider Interface
Defines contract for all content intelligence providers
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

from backend.shared.contracts import NormalizedContent


logger = logging.getLogger(__name__)


class ContentProvider(ABC):
    """
    Abstract base class for content intelligence providers
    
    All providers must implement this interface to ensure consistent behavior
    No provider-specific logic should leak outside this layer
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config or {}
        self.provider_name = self.__class__.__name__
        logger.info(f"Initializing {self.provider_name}")
    
    @abstractmethod
    async def extract_content(
        self,
        url: str,
        **kwargs
    ) -> NormalizedContent:
        """
        Extract content from URL
        
        Args:
            url: URL to extract content from
            **kwargs: Provider-specific parameters
            
        Returns:
            NormalizedContent object
            
        Raises:
            Exception: If extraction fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is healthy and operational
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get provider capabilities
        
        Returns:
            Dictionary describing provider capabilities
        """
        pass
    
    def get_provider_name(self) -> str:
        """
        Get provider name
        
        Returns:
            Provider name
        """
        return self.provider_name
    
    def validate_config(self) -> bool:
        """
        Validate provider configuration
        
        Returns:
            True if configuration is valid
        """
        # Base implementation - override in subclasses if needed
        return True
    
    async def cleanup(self):
        """
        Cleanup provider resources
        Override in subclasses if cleanup is needed
        """
        logger.info(f"Cleaning up {self.provider_name}")
        pass
