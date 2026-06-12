"""
Runtime Cache
TTL-based caching for runtime objects
Thread-safe, snapshot-version aware
NEVER caches CharacterState permanently
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import threading
import logging

from .runtime_builder import RuntimeBuildResult


logger = logging.getLogger(__name__)


class CachedRuntime(BaseModel):
    """Cached runtime object"""
    user_id: str = Field(..., description="User identifier")
    build_result: RuntimeBuildResult = Field(..., description="Build result")
    snapshot_version: int = Field(..., description="Snapshot version when cached")
    cached_at: datetime = Field(..., description="When cached")
    ttl_seconds: int = Field(..., description="TTL in seconds")
    access_count: int = Field(default=0, description="Access count")
    last_accessed: datetime = Field(..., description="Last access time")
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        age = (datetime.utcnow() - self.cached_at).total_seconds()
        return age > self.ttl_seconds
    
    def is_stale(self, current_snapshot_version: int) -> bool:
        """Check if cache is stale (snapshot version changed)"""
        return self.snapshot_version != current_snapshot_version
    
    def update_access(self):
        """Update access tracking"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class RuntimeCache:
    """
    Runtime Cache
    
    Purpose:
    - Avoid rebuilding runtime repeatedly within one interaction
    - TTL-based expiration
    - Snapshot version awareness
    - Thread-safe operations
    - Memory efficient
    
    NEVER caches CharacterState permanently.
    Only caches runtime objects temporarily.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Runtime Cache
        
        Args:
            config: Cache configuration
        """
        self.config = config or {}
        
        # Configuration
        self.default_ttl = self.config.get("default_ttl_seconds", 300)  # 5 minutes
        self.max_cache_size = self.config.get("max_cache_size", 100)
        self.enable_cache = self.config.get("enable_cache", True)
        
        # Cache storage
        self._cache: Dict[str, CachedRuntime] = {}
        self._lock = threading.RLock()
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info(f"RuntimeCache initialized: ttl={self.default_ttl}s, max_size={self.max_cache_size}")
    
    def cache_runtime(
        self,
        user_id: str,
        build_result: RuntimeBuildResult,
        ttl_seconds: Optional[int] = None
    ):
        """
        Cache runtime for user
        
        Args:
            user_id: User identifier
            build_result: Build result to cache
            ttl_seconds: Optional TTL override
        """
        if not self.enable_cache:
            return
        
        try:
            with self._lock:
                # Check cache size
                if len(self._cache) >= self.max_cache_size:
                    self._evict_oldest()
                
                # Get snapshot version
                snapshot_version = 0
                if build_result.character_core:
                    snapshot_version = build_result.character_core.get_snapshot_version()
                
                # Create cached entry
                cached = CachedRuntime(
                    user_id=user_id,
                    build_result=build_result,
                    snapshot_version=snapshot_version,
                    cached_at=datetime.utcnow(),
                    ttl_seconds=ttl_seconds or self.default_ttl,
                    last_accessed=datetime.utcnow()
                )
                
                self._cache[user_id] = cached
                logger.debug(f"Cached runtime for user {user_id}, version {snapshot_version}")
                
        except Exception as e:
            logger.error(f"Error caching runtime: {str(e)}", exc_info=True)
    
    def get_runtime(
        self,
        user_id: str,
        current_snapshot_version: Optional[int] = None
    ) -> Optional[RuntimeBuildResult]:
        """
        Get cached runtime for user
        
        Args:
            user_id: User identifier
            current_snapshot_version: Current snapshot version (for staleness check)
            
        Returns:
            RuntimeBuildResult if cached and valid, None otherwise
        """
        if not self.enable_cache:
            return None
        
        try:
            with self._lock:
                cached = self._cache.get(user_id)
                
                if cached is None:
                    self._misses += 1
                    logger.debug(f"Cache miss for user {user_id}")
                    return None
                
                # Check expiration
                if cached.is_expired():
                    logger.debug(f"Cache expired for user {user_id}")
                    del self._cache[user_id]
                    self._misses += 1
                    return None
                
                # Check staleness
                if current_snapshot_version is not None:
                    if cached.is_stale(current_snapshot_version):
                        logger.debug(f"Cache stale for user {user_id}: cached={cached.snapshot_version}, current={current_snapshot_version}")
                        del self._cache[user_id]
                        self._misses += 1
                        return None
                
                # Cache hit
                cached.update_access()
                self._hits += 1
                logger.debug(f"Cache hit for user {user_id}, access_count={cached.access_count}")
                
                return cached.build_result
                
        except Exception as e:
            logger.error(f"Error getting cached runtime: {str(e)}", exc_info=True)
            return None
    
    def invalidate_runtime(self, user_id: str):
        """
        Invalidate cached runtime for user
        
        Args:
            user_id: User identifier
        """
        try:
            with self._lock:
                if user_id in self._cache:
                    del self._cache[user_id]
                    logger.debug(f"Invalidated cache for user {user_id}")
                    
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}", exc_info=True)
    
    def invalidate_all(self):
        """Invalidate all cached runtimes"""
        try:
            with self._lock:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Invalidated all cache entries: {count} entries")
                
        except Exception as e:
            logger.error(f"Error invalidating all cache: {str(e)}", exc_info=True)
    
    def cleanup_expired(self):
        """Remove expired cache entries"""
        try:
            with self._lock:
                expired_keys = [
                    user_id for user_id, cached in self._cache.items()
                    if cached.is_expired()
                ]
                
                for user_id in expired_keys:
                    del self._cache[user_id]
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}", exc_info=True)
    
    def _evict_oldest(self):
        """Evict oldest cache entry"""
        try:
            if not self._cache:
                return
            
            # Find oldest entry
            oldest_user_id = min(
                self._cache.keys(),
                key=lambda uid: self._cache[uid].cached_at
            )
            
            del self._cache[oldest_user_id]
            self._evictions += 1
            logger.debug(f"Evicted oldest cache entry for user {oldest_user_id}")
            
        except Exception as e:
            logger.error(f"Error evicting cache: {str(e)}", exc_info=True)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Cache statistics
        """
        try:
            with self._lock:
                total_requests = self._hits + self._misses
                hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
                
                return {
                    "cache_size": len(self._cache),
                    "max_cache_size": self.max_cache_size,
                    "hits": self._hits,
                    "misses": self._misses,
                    "evictions": self._evictions,
                    "hit_rate": hit_rate,
                    "enabled": self.enable_cache
                }
                
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}", exc_info=True)
            return {}
    
    def get_cached_users(self) -> List[str]:
        """
        Get list of cached user IDs
        
        Returns:
            List of user IDs
        """
        try:
            with self._lock:
                return list(self._cache.keys())
                
        except Exception as e:
            logger.error(f"Error getting cached users: {str(e)}", exc_info=True)
            return []


def get_runtime_cache() -> RuntimeCache:
    """Get singleton runtime cache instance"""
    if not hasattr(get_runtime_cache, "_instance"):
        get_runtime_cache._instance = RuntimeCache()
    return get_runtime_cache._instance
