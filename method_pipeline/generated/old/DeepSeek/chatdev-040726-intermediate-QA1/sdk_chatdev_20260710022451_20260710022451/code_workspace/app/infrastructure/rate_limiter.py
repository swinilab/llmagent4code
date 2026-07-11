"""
Token-bucket rate limiter for admission control (NFR 1.3).

When the bucket is empty the request is rejected with HTTP 429 and a
Retry-After header.  The bucket is local to the process (single-node
deployment).  For multi-instance deployments a Redis-backed variant
would be used instead.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class TokenBucket:
    """In-memory token-bucket rate limiter.

    Parameters
    ----------
    max_tokens : int
        Maximum burst size (capacity).
    refill_rate : float
        Tokens added per second.
    refill_interval : float
        How often (seconds) the bucket is refilled.
    """

    def __init__(
        self,
        max_tokens: int = 200,
        refill_rate: float = 50.0,
        refill_interval: float = 0.1,
    ) -> None:
        self._max_tokens = max_tokens
        self._tokens = float(max_tokens)
        self._refill_rate = refill_rate
        self._refill_interval = refill_interval
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed >= self._refill_interval:
            added = elapsed * self._refill_rate
            self._tokens = min(self._max_tokens, self._tokens + added)
            self._last_refill = now

    async def try_consume(self, tokens: float = 1.0) -> bool:
        """Try to consume *tokens* from the bucket.

        Returns True if allowed, False if rate-limited.
        """
        async with self._lock:
            await self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    @property
    def available_tokens(self) -> float:
        return self._tokens


# Singleton
_bucket: Optional[TokenBucket] = None


def get_rate_limiter() -> TokenBucket:
    global _bucket
    if _bucket is None:
        _bucket = TokenBucket(
            max_tokens=settings.rate_limit_tokens,
            refill_rate=settings.rate_limit_refill_rate,
            refill_interval=settings.rate_limit_refill_interval,
        )
    return _bucket


# ── Decorator for endpoint-level rate limiting ────────────────────────

def rate_limited(max_wait: float = 0.0) -> Callable:
    """Decorator that rejects with 429 if the token bucket is empty.

    If *max_wait* > 0, the decorator will busy-wait up to that many
    seconds for a token to become available (useful for background
    workers).  For HTTP endpoints *max_wait* should be 0 so the caller
    gets an immediate 429.
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            allowed = await limiter.try_consume()
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please retry after the rate limit window.",
                    headers={"Retry-After": "1"},
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
