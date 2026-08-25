"""NFR 1.1 - Limit Event Response.

Token-bucket admission control. Requests arriving above the configured
sustained rate are rejected with 429 rather than queued, bounding the work the
service will accept per unit time.

The bucket lives in Redis and is mutated by an atomic Lua script, so the limit
holds across every replica of the API process rather than per-process. If Redis
is unreachable the limiter fails open (availability is preferred over strict
enforcement) - see ADR-004.
"""
import logging
import time

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Atomic refill-then-consume. Returns 1 = allowed, 0 = throttled.
_TOKEN_BUCKET_LUA = """
local key      = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill   = tonumber(ARGV[2])
local now      = tonumber(ARGV[3])
local cost     = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local ts     = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  ts = now
end

local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + elapsed * refill)

local allowed = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.ceil(capacity / refill) + 60)
return allowed
"""


class TokenBucketRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._script = redis.register_script(_TOKEN_BUCKET_LUA)
        self.capacity = settings.rate_limit_capacity
        self.refill_rate = settings.rate_limit_refill_per_second

    async def allow(self, identity: str, cost: int = 1) -> bool:
        """Consume `cost` tokens for `identity`; False means throttle now."""
        try:
            allowed = await self._script(
                keys=[f"ratelimit:{identity}"],
                args=[self.capacity, self.refill_rate, time.time(), cost],
            )
            return bool(allowed)
        except Exception:
            # Fail open: the limiter is a protection tactic, not a correctness one.
            logger.warning("rate limiter unavailable; admitting request", exc_info=True)
            return True
