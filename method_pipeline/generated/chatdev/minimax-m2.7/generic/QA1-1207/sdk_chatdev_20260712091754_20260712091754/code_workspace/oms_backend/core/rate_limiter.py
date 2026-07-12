"""
Rate limiting using sliding-window counters stored in Redis.
Provides per-customer and global rate limiting for NFR 1.3.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import NamedTuple

import redis.asyncio as redis

from oms_backend.core.config import get_settings


class RateLimitResult(NamedTuple):
    allowed: bool
    remaining: int
    retry_after_seconds: int | None


async def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        password=settings.redis.password or None,
        decode_responses=True,
    )


class SlidingWindowRateLimiter:
    """
    Sliding window log rate limiter using Redis ZSET.
    Key = f"ratelimit:{scope}:{identifier}"
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        requests_per_minute: int,
        burst: int = 0,
    ):
        self.redis = redis_client
        self.rpm = requests_per_minute
        self.burst = burst

    def _key(self, scope: str, identifier: str) -> str:
        return f"ratelimit:{scope}:{identifier}"

    async def check(self, scope: str, identifier: str) -> RateLimitResult:
        """
        Atomically check and record a request.
        Returns (allowed, remaining, retry_after).
        """
        now_ms = int(time.time() * 1000)
        window_ms = 60 * 1000  # 1-minute window
        window_start = now_ms - window_ms
        key = self._key(scope, identifier)

        pipe = self.redis.pipeline()
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries in window
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {f"{now_ms}": now_ms})
        # Set TTL to clean up
        pipe.expire(key, 120)
        results = await pipe.execute()
        count = results[1]  # zcard result

        if count >= self.rpm:
            # Remove the request we just added (it should not count as allowed)
            await self.redis.zrem(key, f"{now_ms}")
            # Calculate retry-after = time until oldest entry expires
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int((oldest[0][1] + window_ms - now_ms) / 1000) + 1
            else:
                retry_after = 60
            return RateLimitResult(allowed=False, remaining=0, retry_after_seconds=retry_after)

        remaining = max(0, self.rpm - count - 1)
        return RateLimitResult(allowed=True, remaining=remaining, retry_after_seconds=None)


# Global rate limiter instances (initialized at startup)
_global_limiter: SlidingWindowRateLimiter | None = None


async def init_rate_limiters() -> None:
    global _global_limiter
    settings = get_settings()
    client = await get_redis_client()
    _global_limiter = SlidingWindowRateLimiter(
        redis_client=client,
        requests_per_minute=settings.rate_limiting.global_rpm,
        burst=settings.rate_limiting.burst,
    )


async def get_global_limiter() -> SlidingWindowRateLimiter:
    global _global_limiter
    if _global_limiter is None:
        await init_rate_limiters()
    return _global_limiter


async def check_rate_limit(customer_id: uuid.UUID | None = None) -> RateLimitResult:
    """
    Check global rate limit and optionally per-customer rate limit.
    """
    settings = get_settings()
    if not settings.rate_limiting.enabled:
        return RateLimitResult(allowed=True, remaining=999999, retry_after_seconds=None)

    limiter = await get_global_limiter()

    # Global check
    result = await limiter.check("global", "all")
    if not result.allowed:
        return result

    # Per-customer check
    if customer_id:
        customer_limiter = SlidingWindowRateLimiter(
            redis_client=await get_redis_client(),
            requests_per_minute=settings.rate_limiting.per_customer_rpm,
        )
        return await customer_limiter.check("customer", str(customer_id))

    return result
