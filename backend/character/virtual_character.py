"""
Virtual Character
Thin interface over CharacterCore
NO business logic, NO database access, NO LLM calls
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .runtime_builder import RuntimeBuilder, RuntimeBuildResult, get_runtime_builder
from .core import CharacterCore
from .character_state import CharacterState
from .runtime_cache import RuntimeCache, get_runtime_cache


logger = logging.getLogger(__name__)


class VirtualCharacterRequest(BaseModel):
    """Request to virtual character"""
    user_id: str = Field(..., description="User identifier")
    query: Optional[str] = Field(None, description="User query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    request_id: Optional[str] = Field(None, description="Request ID")
    use_cache: bool = Field(default=True, description="Whether to use cache")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Request metadata")


class VirtualCharacterResponse(BaseModel):
    """Response from virtual character"""
    success: bool = Field(..., description="Whether request succeeded")
    character_core: Optional[CharacterCore] = Field(None, description="Character core")
    character_state: Optional[CharacterState] = Field(None, description="Character state")
    runtime_metadata: Dict[str, Any] = Field(default_factory=dict, description="Runtime metadata")
    errors: List[str] = Field(default_factory=list, description="Errors")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    from_cache: bool = Field(default=False, description="Whether served from cache")


class VirtualCharacter:
    """
    Virtual Character - Thin Runtime Interface
    
    Purpose:
    - Receive requests
    - Invoke Runtime Builder
    - Generate CharacterState
    - Expose runtime metadata
    - Return runtime objects
    
    This is intentionally lightweight.
    
    MUST NOT:
    - Access PostgreSQL directly
    - Generate responses
    - Call LLMs
    - Perform reasoning
    - Perform retrieval
    
    Everything comes from Runtime Builder.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Virtual Character
        
        Args:
            config: Character configuration
        """
        self.config = config or {}
        
        # Get dependencies
        self.runtime_builder = get_runtime_builder()
        self.runtime_cache = get_runtime_cache()
        
        # Configuration
        self.enable_cache = self.config.get("enable_cache", True)
        
        logger.info("VirtualCharacter initialized")
    
    def process_request(
        self,
        request: VirtualCharacterRequest
    ) -> VirtualCharacterResponse:
        """
        Process character request
        
        Args:
            request: Virtual character request
            
        Returns:
            VirtualCharacterResponse
        """
        try:
            logger.info(f"Processing request for user {request.user_id}")
            
            # Check cache if enabled
            from_cache = False
            if self.enable_cache and request.use_cache:
                cached_result = self.runtime_cache.get_runtime(request.user_id)
                if cached_result is not None:
                    logger.info(f"Serving runtime from cache for user {request.user_id}")
                    from_cache = True
                    
                    return VirtualCharacterResponse(
                        success=True,
                        character_core=cached_result.character_core,
                        character_state=cached_result.character_state,
                        runtime_metadata=cached_result.metadata,
                        from_cache=True
                    )
            
            # Build runtime
            build_result = self.runtime_builder.build_runtime(
                user_id=request.user_id,
                current_query=request.query,
                conversation_id=request.conversation_id,
                session_id=request.session_id,
                request_id=request.request_id
            )
            
            # Cache if successful
            if build_result.success and self.enable_cache:
                self.runtime_cache.cache_runtime(
                    user_id=request.user_id,
                    build_result=build_result
                )
            
            # Build response
            response = VirtualCharacterResponse(
                success=build_result.success,
                character_core=build_result.character_core,
                character_state=build_result.character_state,
                runtime_metadata=build_result.metadata,
                errors=build_result.errors,
                warnings=build_result.warnings,
                from_cache=from_cache
            )
            
            logger.info(f"Request processed: success={response.success}, from_cache={from_cache}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return VirtualCharacterResponse(
                success=False,
                errors=[f"Request processing failed: {str(e)}"],
                runtime_metadata={"error": True}
            )
    
    def get_character_state(
        self,
        user_id: str,
        use_cache: bool = True
    ) -> Optional[CharacterState]:
        """
        Get character state for user
        
        Args:
            user_id: User identifier
            use_cache: Whether to use cache
            
        Returns:
            CharacterState or None
        """
        try:
            request = VirtualCharacterRequest(
                user_id=user_id,
                use_cache=use_cache
            )
            
            response = self.process_request(request)
            
            if response.success:
                return response.character_state
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting character state: {str(e)}", exc_info=True)
            return None
    
    def get_character_core(
        self,
        user_id: str,
        use_cache: bool = True
    ) -> Optional[CharacterCore]:
        """
        Get character core for user
        
        Args:
            user_id: User identifier
            use_cache: Whether to use cache
            
        Returns:
            CharacterCore or None
        """
        try:
            request = VirtualCharacterRequest(
                user_id=user_id,
                use_cache=use_cache
            )
            
            response = self.process_request(request)
            
            if response.success:
                return response.character_core
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting character core: {str(e)}", exc_info=True)
            return None
    
    def invalidate_cache(self, user_id: str):
        """
        Invalidate cache for user
        
        Args:
            user_id: User identifier
        """
        try:
            self.runtime_cache.invalidate_runtime(user_id)
            logger.info(f"Cache invalidated for user {user_id}")
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}", exc_info=True)
    
    def get_runtime_metadata(self, user_id: str) -> Dict[str, Any]:
        """
        Get runtime metadata for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Runtime metadata
        """
        try:
            request = VirtualCharacterRequest(user_id=user_id)
            response = self.process_request(request)
            
            return response.runtime_metadata
            
        except Exception as e:
            logger.error(f"Error getting runtime metadata: {str(e)}", exc_info=True)
            return {"error": str(e)}


def get_virtual_character() -> VirtualCharacter:
    """Get singleton virtual character instance"""
    if not hasattr(get_virtual_character, "_instance"):
        get_virtual_character._instance = VirtualCharacter()
    return get_virtual_character._instance
