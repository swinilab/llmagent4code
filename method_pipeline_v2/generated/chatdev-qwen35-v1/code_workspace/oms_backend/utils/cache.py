"""
Cache utilities for NFR 1.2 - Maintain Multiple copies of Data
Uses Redis for distributed caching with fallback to in-memory cache
"""
import json
from typing import Any, Optional
from datetime import timedelta
import redis
from oms_backend.config import settings


class CacheManager:
    """
    Cache manager for maintaining multiple copies of data.
    Satisfies NFR 1.2: Maintain Multiple copies of Data through caching.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Optional Redis client instance
        """
        self.redis = redis_client
        self.default_ttl = settings.redis_cache_ttl
        self._memory_cache = {}
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not settings.enable_caching:
            return None
            
        if self.redis:
            try:
                value = self.redis.get(f"cache:{key}")
                if value:
                    return json.loads(value)
                return None
            except redis.RedisError:
                # Graceful degradation: fall back to memory cache
                return self._memory_cache.get(key)
        else:
            return self._memory_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not settings.enable_caching:
            return False
            
        ttl = ttl or self.default_ttl
        
        if self.redis:
            try:
                self.redis.setex(f"cache:{key}", ttl, json.dumps(value))
                return True
            except redis.RedisError:
                # Graceful degradation: store in memory cache
                self._memory_cache[key] = value
                return True
        else:
            self._memory_cache[key] = value
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if self.redis:
            try:
                self.redis.delete(f"cache:{key}")
            except redis.RedisError:
                pass
        self._memory_cache.pop(key, None)
        return True
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "customer:*")
            
        Returns:
            Number of keys invalidated
        """
        count = 0
        if self.redis:
            try:
                keys = self.redis.keys(f"cache:{pattern}")
                if keys:
                    count = self.redis.delete(*keys)
            except redis.RedisError:
                pass
        # Also clear from memory cache
        keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(pattern.split("*")[0])]
        for k in keys_to_delete:
            del self._memory_cache[k]
            count += 1
        return count


# Global cache manager instance
cache_manager = CacheManager()
