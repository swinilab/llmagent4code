"""In-process token bucket rate limiter for admission control (NFR 1.3).

Algorithm: Token Bucket
  - Capacity: 2000 tokens (burst allowance)
  - Refill rate: 500 tokens/second (sustained throughput)
  - Implementation: in-process (not shared Redis) because we run on a single
    node. For multi-node, a Redis-backed variant would be used.

Behavior on rejection:
  - HTTP 429 Too Many Requests
  - Retry-After header: seconds until next token available

Memory ceiling: O(1) per limiter instance — two floats and a timestamp.
No unbounded growth possible.
"""

import time
from dataclasses import dataclass
from typing import Optional

from app.config import settings


@dataclass
class TokenBucketResult:
    """Result of a rate-limit check."""
    allowed: bool
    retry_after_seconds: float


class TokenBucketRateLimiter:
    """In-process token bucket rate limiter.

    Thread-safe for async use (single-threaded event loop).
    """

    def __init__(
        self,
        capacity: int = settings.rate_limit_capacity,
        refill_per_second: float = settings.rate_limit_refill_per_second,
    ) -> None:
        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_per_second)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> TokenBucketResult:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume (default 1 per request).

        Returns:
            TokenBucketResult with allowed flag and retry-after seconds.
        """
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return TokenBucketResult(allowed=True, retry_after_seconds=0.0)
        # Calculate retry-after: time until enough tokens are available
        deficit = tokens - self._tokens
        retry_after = deficit / self._refill_per_second
        return TokenBucketResult(allowed=False, retry_after_seconds=retry_after)

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens."""
        self._refill()
        return self._tokens


# Singleton instance for the checkout path
checkout_rate_limiter = TokenBucketRateLimiter()
