"""
Redis-based cache for hot read paths (product search/browse).
"""
import json
from typing import Optional, Any
from redis.asyncio import Redis, ConnectionPool
from oms.config import settings


class Cache:
    """Redis-backed cache with TTL support for read-heavy endpoints."""

    def __init__(self, redis_url: str = settings.redis_url):
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._redis_url = redis_url

    async def initialize(self) -> None:
        """Create the Redis connection pool."""
        self._pool = ConnectionPool.from_url(
            self._redis_url,
            max_connections=settings.redis_pool_size,
            decode_responses=True,
        )
        self._redis = Redis(connection_pool=self._pool)

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        if self._redis is None:
            return None
        data = await self._redis.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    async def set(self, key: str, value: Any, ttl: int = settings.product_cache_ttl) -> None:
        """Store a value in cache with TTL."""
        if self._redis is None:
            return
        serialized = json.dumps(value, default=str)
        await self._redis.setex(key, ttl, serialized)

    async def delete(self, key: str) -> None:
        """Invalidate a cache key."""
        if self._redis is None:
            return
        await self._redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching a pattern (e.g., 'product:*')."""
        if self._redis is None:
            return
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()


# Singleton instance
cache = Cache()


async def get_cache() -> Cache:
    """FastAPI dependency to get the cache instance."""
    return cache
