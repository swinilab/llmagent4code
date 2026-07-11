"""
Token-bucket rate limiter for admission control on the checkout path.
Implements backpressure: when tokens are exhausted, the request is rejected
with HTTP 429 and a Retry-After header.
"""
import asyncio
import time
from typing import Optional
from oms.config import settings


class TokenBucketRateLimiter:
    """
    Token-bucket rate limiter.
    Each request consumes one token. Tokens refill at a fixed rate.
    When the bucket is empty, requests are denied.
    """

    def __init__(
        self,
        capacity: int = settings.rate_limit_tokens,
        refill_rate: float = settings.rate_limit_refill_rate,
        refill_interval: float = settings.rate_limit_refill_interval,
    ):
        self._capacity = capacity
        self._tokens = float(capacity)
        self._refill_rate = refill_rate
        self._refill_interval = refill_interval
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed >= self._refill_interval:
            tokens_to_add = elapsed * self._refill_rate
            self._tokens = min(self._capacity, self._tokens + tokens_to_add)
            self._last_refill = now

    async def acquire(self) -> bool:
        """
        Try to acquire a token.
        Returns True if allowed, False if rate-limited.
        """
        async with self._lock:
            await self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    async def get_available_tokens(self) -> float:
        """Thread-safe read of available tokens (for metrics)."""
        async with self._lock:
            await self._refill()
            return self._tokens

    @property
    def capacity(self) -> int:
        return self._capacity


# Singleton instance
rate_limiter = TokenBucketRateLimiter()


async def get_rate_limiter() -> TokenBucketRateLimiter:
    """FastAPI dependency to get the rate limiter."""
    return rate_limiter
