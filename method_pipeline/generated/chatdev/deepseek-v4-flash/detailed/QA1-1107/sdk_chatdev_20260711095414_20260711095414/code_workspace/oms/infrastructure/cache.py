"""
Redis-backed cache-aside layer for product search/browse.
TTL = 60 s → max staleness window = 60 s (acceptable for product data).
Search result cache TTL = 30 s (shorter because search queries vary more).
Invalidation triggered on price/stock updates.
"""
from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis

from oms.infrastructure.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
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


# ── Product cache helpers ────────────────────────────────────────────────────

def _product_key(product_id: UUID) -> str:
    return f"product:{product_id}"


async def get_cached_product(product_id: UUID) -> Optional[dict]:
    """Cache-aside read: return cached dict or None."""
    r = await get_redis()
    data = await r.get(_product_key(product_id))
    if data:
        return json.loads(data)
    return None


async def set_cached_product(product_id: UUID, product_data: dict) -> None:
    """Write-through cache after DB read."""
    r = await get_redis()
    await r.setex(
        _product_key(product_id),
        settings.product_cache_ttl_seconds,
        json.dumps(product_data, default=str),
    )


async def invalidate_product_cache(product_id: UUID) -> None:
    """Call on price/stock update to keep staleness window bounded."""
    r = await get_redis()
    await r.delete(_product_key(product_id))


# ── Search result cache helpers ──────────────────────────────────────────────

async def get_cached_search_results(cache_key: str) -> Optional[list[str]]:
    """Return cached list of product ID strings, or None."""
    r = await get_redis()
    data = await r.get(f"search:{cache_key}")
    if data:
        return json.loads(data)
    return None


async def set_cached_search_results(cache_key: str, product_ids: list[str], ttl: int = 30) -> None:
    """Cache search result IDs with a shorter TTL (default 30s)."""
    r = await get_redis()
    await r.setex(f"search:{cache_key}", ttl, json.dumps(product_ids))


# ── Idempotency key store ─────────────────────────────────────────────────────

def _idempotency_key(key: str) -> str:
    return f"idempotency:{key}"


async def idempotency_check(key: str) -> Optional[str]:
    """Return cached result if key already processed, else None."""
    r = await get_redis()
    return await r.get(_idempotency_key(key))


async def idempotency_set(key: str, result: str) -> None:
    """Store idempotency result with TTL."""
    r = await get_redis()
    await r.setex(_idempotency_key(key), settings.idempotency_ttl_seconds, result)
