"""Redis-backed cache-aside layer for product search/browse.

Cache strategy: cache-aside (lazy loading)
  - On read: check cache first; on miss, load from DB, populate cache, return.
  - On write (price/stock update): invalidate cache entry explicitly.
  - Eviction policy: Redis LRU (allkeys-lru) — automatically evicts least
    recently used keys when memory limit is reached.

TTL: 60 seconds (configurable via settings.product_cache_ttl_seconds)
Max staleness window: TTL + clock skew (~2s) ≈ 62 seconds.
Acceptable for e-commerce browse: price/stock updates propagate within ~1 min.

Cache key format: "product:{id}" for single product, "product:search:{query_hash}" for search results.
"""

import hashlib
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings

# Redis client with sized connection pool
redis_client: Optional[aioredis.Redis] = None


async def init_cache() -> None:
    """Initialize the Redis connection pool."""
    global redis_client
    redis_client = aioredis.from_url(
        settings.redis_url,
        max_connections=settings.redis_pool_size,  # 20 connections
        decode_responses=True,
    )
    # Configure LRU eviction at Redis level (allkeys-lru)
    await redis_client.config_set("maxmemory-policy", "allkeys-lru")


async def close_cache() -> None:
    """Close the Redis connection pool."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def _search_cache_key(query: str, page: int, page_size: int) -> str:
    """Generate a deterministic cache key for a search query."""
    raw = f"{query}:{page}:{page_size}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"product:search:{h}"


async def get_cached_product(product_id: str) -> Optional[dict[str, Any]]:
    """Get a product from cache by ID.

    Returns:
        Parsed dict if found, None otherwise.
    """
    if redis_client is None:
        return None
    key = f"product:{product_id}"
    data = await redis_client.get(key)
    if data is None:
        return None
    return json.loads(data)


async def set_cached_product(product_id: str, product_data: dict[str, Any]) -> None:
    """Store a product in cache with TTL."""
    if redis_client is None:
        return
    key = f"product:{product_id}"
    await redis_client.setex(
        key,
        settings.product_cache_ttl_seconds,
        json.dumps(product_data, default=str),
    )


async def invalidate_product_cache(product_id: str) -> None:
    """Remove a product from cache (called on price/stock update)."""
    if redis_client is None:
        return
    key = f"product:{product_id}"
    await redis_client.delete(key)


async def get_cached_search(query: str, page: int, page_size: int) -> Optional[list[dict[str, Any]]]:
    """Get cached search results."""
    if redis_client is None:
        return None
    key = _search_cache_key(query, page, page_size)
    data = await redis_client.get(key)
    if data is None:
        return None
    return json.loads(data)


async def set_cached_search(
    query: str, page: int, page_size: int, results: list[dict[str, Any]]
) -> None:
    """Cache search results with TTL."""
    if redis_client is None:
        return
    key = _search_cache_key(query, page, page_size)
    await redis_client.setex(
        key,
        settings.product_cache_ttl_seconds,
        json.dumps(results, default=str),
    )


async def invalidate_search_cache() -> None:
    """Invalidate all search result caches when any product changes.

    This is a coarse invalidation. For production, a more granular approach
    (e.g., tagging) would be used, but for the scope of this system, clearing
    search cache on any product update is acceptable given the 60s TTL.
    """
    if redis_client is None:
        return
    cursor = 0
    pattern = "product:search:*"
    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break
