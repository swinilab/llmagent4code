"""
Redis-backed cache for hot read paths (product search/browse).

Invalidation policy:
  - Products are cached with a TTL (default 60 s).
  - On product update (PUT /products/{id}) the cache key is evicted.
  - On stock change (order placement) the product cache is evicted.
  - A background TTL ensures stale data is eventually refreshed.
"""

from __future__ import annotations

import json
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return a singleton Redis connection."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


# ── Product cache helpers ──────────────────────────────────────────────

PRODUCT_CACHE_PREFIX = "product:"
PRODUCT_SEARCH_CACHE_PREFIX = "product_search:"


def _product_key(product_id: int) -> str:
    return f"{PRODUCT_CACHE_PREFIX}{product_id}"


def _search_key(query: str, page: int, page_size: int) -> str:
    return f"{PRODUCT_SEARCH_CACHE_PREFIX}{query}:{page}:{page_size}"


async def cache_product(product_id: int, data: dict, ttl: int | None = None) -> None:
    r = await get_redis()
    await r.setex(
        _product_key(product_id),
        ttl or settings.redis_product_cache_ttl,
        json.dumps(data, default=str),
    )


async def get_cached_product(product_id: int) -> Optional[dict]:
    r = await get_redis()
    raw = await r.get(_product_key(product_id))
    if raw is None:
        return None
    return json.loads(raw)


async def invalidate_product_cache(product_id: int) -> None:
    r = await get_redis()
    await r.delete(_product_key(product_id))


async def cache_search_result(
    query: str, page: int, page_size: int, data: dict, ttl: int = 30
) -> None:
    r = await get_redis()
    await r.setex(
        _search_key(query, page, page_size),
        ttl,
        json.dumps(data, default=str),
    )


async def get_cached_search_result(
    query: str, page: int, page_size: int
) -> Optional[dict]:
    r = await get_redis()
    raw = await r.get(_search_key(query, page, page_size))
    if raw is None:
        return None
    return json.loads(raw)
