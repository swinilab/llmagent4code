"""
Redis-backed cache-aside layer for hot reads (NFR 1.1, NFR 1.2).

Cache-aside pattern:
  1. Read from cache; if hit, return.
  2. If miss, read from DB, write to cache, return.
  3. Writes invalidate the cache entry.

TTL is set per entity type to balance freshness vs. hit rate.
"""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Callable, Optional, TypeVar

from redis.asyncio import Redis

from oms.config import settings

T = TypeVar("T")

# Default TTLs per entity type (in seconds)
CACHE_TTL: dict[str, int] = {
    "product": 300,       # 5 min — products change infrequently
    "customer": 600,      # 10 min
    "order": 120,         # 2 min — orders change frequently
    "invoice": 300,       # 5 min
    "payment": 120,       # 2 min
}

_redis: Optional[Redis] = None


async def get_redis() -> Redis:
    """Lazy-init Redis connection (singleton)."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _redis


async def close_redis() -> None:
    """Close the Redis connection gracefully."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


def _cache_key(entity_type: str, entity_id: str) -> str:
    return f"oms:{entity_type}:{entity_id}"


async def cache_get(entity_type: str, entity_id: str) -> Optional[dict]:
    """Get a cached entity by type and id."""
    r = await get_redis()
    raw = await r.get(_cache_key(entity_type, entity_id))
    if raw is None:
        return None
    return json.loads(raw)


async def cache_set(
    entity_type: str,
    entity_id: str,
    data: dict,
    ttl: Optional[int] = None,
) -> None:
    """Set a cached entity with optional TTL override."""
    r = await get_redis()
    ttl = ttl or CACHE_TTL.get(entity_type, 120)
    await r.setex(_cache_key(entity_type, entity_id), ttl, json.dumps(data, default=str))


async def cache_delete(entity_type: str, entity_id: str) -> None:
    """Delete a cached entity (called on write)."""
    r = await get_redis()
    await r.delete(_cache_key(entity_type, entity_id))


async def cache_invalidate_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern."""
    r = await get_redis()
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor, match=pattern, count=100)
        if keys:
            await r.delete(*keys)
        if cursor == 0:
            break


async def check_cache_health() -> bool:
    """Health-check: ping Redis (NFR 2.2)."""
    try:
        r = await get_redis()
        await r.ping()
        return True
    except Exception:
        return False
