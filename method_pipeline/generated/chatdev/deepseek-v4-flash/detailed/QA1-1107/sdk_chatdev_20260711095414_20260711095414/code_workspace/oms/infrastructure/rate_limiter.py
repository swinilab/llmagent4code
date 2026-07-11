"""
In-process token-bucket rate limiter (NFR 1.3a).
Admission control for the checkout path.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Optional

from oms.infrastructure.config import settings


class TokenBucket:
    """
    Thread-safe (asyncio) token bucket.
    - capacity: max burst size
    - refill_rate: tokens added per second
    """

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume *tokens*; return True if allowed, False if denied."""
        async with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    @property
    def available_tokens(self) -> float:
        return self._tokens


# Singleton used by the checkout path
checkout_rate_limiter = TokenBucket(
    capacity=settings.rate_limit_capacity,       # 5000 burst
    refill_rate=settings.rate_limit_refill_per_second,  # 1000/s sustained
)
