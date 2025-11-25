"""
Caching Service Module

This module implements an in-memory caching system with TTL support.
It demonstrates caching patterns, decorators, and cache invalidation strategies.

Key Features:
- In-memory cache with TTL
- Decorator-based caching
- Cache invalidation
- Thread-safe operations
- Cache statistics

Usage:
    from app.services.cache import get_cache, cache_result
    
    cache = get_cache()
    await cache.set("key", "value", ttl=300)
    value = await cache.get("key")
    
    @cache_result(ttl=60)
    async def expensive_function(arg):
        return result
"""

import asyncio
from typing import Any, Optional, Callable, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """
    Represents a single cache entry with expiration.
    
    Attributes:
        value: Cached value
        expires_at: Expiration timestamp
        created_at: Creation timestamp
        hits: Number of times this entry was accessed
    """
    value: Any
    expires_at: datetime
    created_at: datetime
    hits: int = 0
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return datetime.utcnow() > self.expires_at
    
    def increment_hits(self) -> None:
        """Increment hit counter."""
        self.hits += 1


class CacheService:
    """
    In-memory cache service with TTL support.
    
    This class provides a thread-safe caching mechanism suitable for
    single-instance deployments. For distributed systems, use Redis.
    
    Example:
        >>> cache = CacheService()
        >>> await cache.set("user:1", {"name": "John"}, ttl=300)
        >>> user = await cache.get("user:1")
        >>> await cache.delete("user:1")
    """
    
    def __init__(self, default_ttl: int = 300) -> None:
        """
        Initialize cache service.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
        }
        
        # Start background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("CacheService initialized", default_ttl=default_ttl)
    
    async def start_cleanup_task(self) -> None:
        """
        Start background task to clean up expired entries.
        
        This task runs periodically to remove expired cache entries.
        """
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache cleanup task started")
    
    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cache cleanup task stopped")
    
    async def _cleanup_loop(self) -> None:
        """
        Background loop to clean up expired entries.
        
        Runs every 60 seconds to remove expired cache entries.
        """
        while True:
            try:
                await asyncio.sleep(60)  # Clean up every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cache cleanup", error=str(e))
    
    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._stats["evictions"] += 1
            
            if expired_keys:
                logger.debug(
                    "Cleaned up expired cache entries",
                    count=len(expired_keys)
                )
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
            
        Example:
            >>> value = await cache.get("user:123")
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                return None
            
            entry.increment_hits()
            self._stats["hits"] += 1
            
            logger.debug("Cache hit", key=key, hits=entry.hits)
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set a value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not provided)
            
        Example:
            >>> await cache.set("user:123", user_data, ttl=300)
        """
        if ttl is None:
            ttl = self._default_ttl
        
        async with self._lock:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            entry = CacheEntry(
                value=value,
                expires_at=expires_at,
                created_at=datetime.utcnow()
            )
            
            self._cache[key] = entry
            self._stats["sets"] += 1
            
            logger.debug("Cache set", key=key, ttl=ttl)
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed, False otherwise
            
        Example:
            >>> success = await cache.delete("user:123")
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
                logger.debug("Cache delete", key=key)
                return True
            return False
    
    async def clear(self) -> None:
        """
        Clear all cache entries.
        
        Example:
            >>> await cache.clear()
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared", entries_removed=count)
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return True
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
            
        Example:
            >>> stats = await cache.get_stats()
            >>> print(stats["hits"], stats["misses"])
        """
        async with self._lock:
            hit_rate = 0.0
            total_requests = self._stats["hits"] + self._stats["misses"]
            if total_requests > 0:
                hit_rate = (self._stats["hits"] / total_requests) * 100
            
            return {
                **self._stats,
                "entries": len(self._cache),
                "hit_rate_percent": round(hit_rate, 2),
            }
    
    async def get_keys_by_pattern(self, pattern: str) -> list[str]:
        """
        Get all keys matching a pattern (simple prefix matching).
        
        Args:
            pattern: Key prefix pattern
            
        Returns:
            List of matching keys
            
        Example:
            >>> keys = await cache.get_keys_by_pattern("user:")
        """
        async with self._lock:
            return [
                key for key in self._cache.keys()
                if key.startswith(pattern)
            ]
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Useful for cache invalidation strategies.
        
        Args:
            pattern: Key prefix pattern
            
        Returns:
            Number of keys invalidated
            
        Example:
            >>> count = await cache.invalidate_pattern("user:")
        """
        keys = await self.get_keys_by_pattern(pattern)
        for key in keys:
            await self.delete(key)
        
        logger.info("Cache pattern invalidated", pattern=pattern, count=len(keys))
        return len(keys)


def generate_cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate a cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        MD5 hash of the arguments
        
    Example:
        >>> key = generate_cache_key("users", page=1, limit=10)
    """
    # Create a string representation of arguments
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    # Generate MD5 hash
    return hashlib.md5(key_data.encode()).hexdigest()


def cache_result(ttl: int = 300, key_prefix: str = "") -> Callable:
    """
    Decorator to cache function results.
    
    This decorator caches the return value of async functions based on
    their arguments.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorator function
        
    Example:
        >>> @cache_result(ttl=60, key_prefix="user")
        >>> async def get_user(user_id: int):
        >>>     # Expensive operation
        >>>     return user_data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{generate_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cache = get_cache()
            cached_value = await cache.get(cache_key)
            
            if cached_value is not None:
                logger.debug("Using cached result", function=func.__name__)
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            
            logger.debug("Cached function result", function=func.__name__, ttl=ttl)
            return result
        
        return wrapper
    return decorator


# Global cache instance (singleton pattern)
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    """
    Get the global cache instance.
    
    Returns:
        Global CacheService instance
        
    Example:
        >>> cache = get_cache()
        >>> await cache.set("key", "value")
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService(default_ttl=settings.CACHE_TTL)
    return _cache_instance


async def init_cache() -> None:
    """Initialize cache and start cleanup task."""
    cache = get_cache()
    await cache.start_cleanup_task()
    logger.info("Cache initialized with cleanup task")


async def shutdown_cache() -> None:
    """Shutdown cache and cleanup task."""
    cache = get_cache()
    await cache.stop_cleanup_task()
    logger.info("Cache shutdown complete")
