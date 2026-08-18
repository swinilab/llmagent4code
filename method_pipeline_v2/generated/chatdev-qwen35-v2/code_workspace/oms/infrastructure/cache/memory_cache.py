"""
In-memory cache implementation for NFR 1.2 Maintain Multiple copies of Data
Provides caching layer for frequently accessed data
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Dict
from oms.config.app_config import AppConfig

config = AppConfig()

class MemoryCache:
    """
    Singleton in-memory cache with TTL support
    Implements NFR 1.2 via caching tactic
    """
    _instance = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def get_instance(cls) -> 'MemoryCache':
        """Get singleton cache instance"""
        if cls._instance is None:
            cls._instance = MemoryCache()
        return cls._instance
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        Returns None if key doesn't exist or is expired
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry['expires_at'] < datetime.now(timezone.utc):
            await self.delete(key)
            return None
        
        return entry['value']
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Set value in cache with TTL
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=ttl)
        }
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        Returns True if key existed, False otherwise
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern
        Returns count of invalidated entries
        """
        import re
        compiled = re.compile(pattern)
        keys_to_delete = [k for k in self._cache.keys() if compiled.match(k)]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)

__all__ = ['MemoryCache']
