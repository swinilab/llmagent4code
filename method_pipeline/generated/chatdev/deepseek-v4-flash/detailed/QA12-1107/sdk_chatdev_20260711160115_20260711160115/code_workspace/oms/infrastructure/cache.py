"""
Redis-backed cache-aside layer for latency-sensitive read paths.

Cache-aside pattern:
  1. Read from cache (Redis).
  2. On miss, read from DB, write to cache with TTL.
  3. On write, invalidate cache entry.

Connection pool sizing (per NFR 1.2):
  Redis pool max_connections = workers * 2 = 8 * 2 = 16
  Using redis.asyncio for non-blocking I/O.

Eviction policy: allkeys-lru (Redis default, but we set it explicitly).

Also wires the Redis client into:
  - The global rate limiter for shared token-bucket state across workers (NFR 1.3)
  - All circuit breakers for shared state across workers (NFR 2.1)
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

import orjson
from redis.asyncio import ConnectionPool, Redis

from oms.config import settings


class RedisCache:
    """Async cache-aside helper backed by Redis."""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def connect(self):
        """Initialize connection pool and wire into rate limiter and circuit breakers."""
        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=16,
            decode_responses=True,
        )
        self._client = Redis(connection_pool=self._pool)
        # Configure eviction policy (best-effort)
        try:
            await self._client.config_set("maxmemory-policy", "allkeys-lru")
        except Exception:
            pass  # non-fatal if we lack CONFIG permission

        # Wire Redis client into the global rate limiter for shared state
        from oms.infrastructure.rate_limiter import rate_limiter
        rate_limiter.set_redis_client(self._client)

        # Wire Redis client into all circuit breakers for shared state
        from oms.infrastructure.circuit_breaker import wire_circuit_breakers_to_redis
        wire_circuit_breakers_to_redis(self._client)

    async def disconnect(self):
        """Close connections."""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.disconnect()

    async def ping(self) -> bool:
        """Check if Redis is reachable. Returns True if healthy."""
        try:
            if self._client is None:
                return False
            await self._client.ping()
            return True
        except Exception:
            return False

    async def get(self, key: str) -> Optional[dict]:
        """Get cached value as dict, or None."""
        raw = await self._client.get(key)
        if raw is None:
            return None
        return orjson.loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: int = 60):
        """Set cached value with TTL."""
        raw = orjson.dumps(value)
        await self._client.setex(key, ttl_seconds, raw)

    async def delete(self, key: str):
        """Invalidate cache entry."""
        await self._client.delete(key)

    async def get_or_compute(
        self, key: str, ttl_seconds: int, loader: Callable
    ) -> dict:
        """Cache-aside: return cached value or compute, cache, and return."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await loader()
        await self.set(key, value, ttl_seconds)
        return value

    async def invalidate_pattern(self, pattern: str):
        """Delete all keys matching a glob pattern."""
        cursor = 0
        while True:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self._client.delete(*keys)
            if cursor == 0:
                break


# Singleton
cache = RedisCache()
