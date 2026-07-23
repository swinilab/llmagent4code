"""
Token-bucket rate limiter for admission control (NFR 1.3).

Algorithm:
  - Bucket holds up to `burst` tokens.
  - Tokens refill at `refill_rate` tokens/second.
  - Each request consumes 1 token.
  - If insufficient tokens, request is rejected with 429 Too Many Requests.

Supports two modes:
  1. Redis-backed (shared across workers) — preferred for multi-worker deployment.
  2. In-memory (per-worker) — fallback when Redis is unavailable.

For 5,000 concurrent sessions with avg queueing < 50ms:
  refill_rate = 5000 tokens/s (sustained throughput)
  burst = 10000 tokens (absorb 3x spike over ~2s)

With 8 workers, the Redis-backed limiter ensures the aggregate rate across
all workers does not exceed the configured limit. Without Redis, each worker
would independently allow up to `burst` tokens, giving an effective limit
of 8x the configured value.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from oms.config import settings

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter.

    Uses Redis for shared state when available, falling back to in-memory
    per-worker state if Redis is not configured or unreachable.

    The Redis-backed mode uses a Lua script for atomic token consumption,
    ensuring correctness across multiple workers.
    """

    def __init__(self, refill_rate: float, burst: int):
        self._refill_rate = refill_rate
        self._burst = burst
        # In-memory fallback state
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._redis_client = None

    def set_redis_client(self, client):
        """Set the Redis client for shared-state mode."""
        self._redis_client = client

    async def try_consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed, False if rate-limited.

        Uses Redis-backed token bucket when available, otherwise falls back
        to in-memory per-worker state.
        """
        if self._redis_client is not None:
            return await self._try_consume_redis(tokens)
        return await self._try_consume_memory(tokens)

    async def _try_consume_redis(self, tokens: int) -> bool:
        """Redis-backed token consumption using a Lua script for atomicity.

        The script:
          1. Gets current token count (or initializes to burst).
          2. Calculates refill based on elapsed time.
          3. If enough tokens, decrements and returns 1.
          4. Otherwise returns 0.
        """
        key = "rate_limiter:tokens"
        last_refill_key = "rate_limiter:last_refill"
        now = time.time()

        lua_script = """
        local key = KEYS[1]
        local last_refill_key = KEYS[2]
        local refill_rate = tonumber(ARGV[1])
        local burst = tonumber(ARGV[2])
        local tokens_needed = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        local tokens = redis.call('GET', key)
        if not tokens then
            tokens = burst
        else
            tokens = tonumber(tokens)
        end

        local last_refill = redis.call('GET', last_refill_key)
        if last_refill then
            last_refill = tonumber(last_refill)
            local elapsed = now - last_refill
            if elapsed > 0 then
                tokens = math.min(burst, tokens + elapsed * refill_rate)
            end
        end

        if tokens >= tokens_needed then
            tokens = tokens - tokens_needed
            redis.call('SET', key, tokens)
            redis.call('SET', last_refill_key, now)
            return 1
        else
            redis.call('SET', key, tokens)
            redis.call('SET', last_refill_key, now)
            return 0
        end
        """
        try:
            result = await self._redis_client.eval(
                lua_script,
                2,
                key,
                last_refill_key,
                str(self._refill_rate),
                str(self._burst),
                str(tokens),
                str(now),
            )
            return result == 1
        except Exception as e:
            logger.warning("Redis rate limiter failed, falling back to in-memory: %s", e)
            return await self._try_consume_memory(tokens)

    async def _try_consume_memory(self, tokens: int) -> bool:
        """In-memory token consumption (per-worker fallback)."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._refill_rate)
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def get_available_tokens(self) -> float:
        """Get the current number of available tokens.

        For Redis mode, reads from Redis. For in-memory mode, returns local state.
        """
        if self._redis_client is not None:
            try:
                key = "rate_limiter:tokens"
                last_refill_key = "rate_limiter:last_refill"
                tokens_raw = await self._redis_client.get(key)
                last_refill_raw = await self._redis_client.get(last_refill_key)
                if tokens_raw is not None:
                    tokens = float(tokens_raw)
                    if last_refill_raw is not None:
                        elapsed = time.time() - float(last_refill_raw)
                        if elapsed > 0:
                            tokens = min(self._burst, tokens + elapsed * self._refill_rate)
                    return tokens
                return float(self._burst)
            except Exception:
                pass
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            return min(self._burst, self._tokens + elapsed * self._refill_rate)

    @property
    def available_tokens(self) -> float:
        """Synchronous property returning in-memory tokens (may be stale in Redis mode).

        For accurate reading in Redis mode, use get_available_tokens() async method.
        """
        return self._tokens


# Global rate limiter instance
rate_limiter = TokenBucket(
    refill_rate=settings.rate_limit_refill_rate,
    burst=settings.rate_limit_burst,
)
