"""NFR 1.2 - Maintain Multiple Copies of Data (caching half).

A read-through cache in front of the entity read path. The second copy of the
data is the Postgres streaming replica (see database.py); this module is the
third, hottest copy.

Every call is wrapped in a timeout (NFR 2.1 Exception Detection / timeout) and
every failure degrades to a cache miss rather than an error (NFR 2.2).
"""
import asyncio
import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class EntityCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._ttl = settings.cache_ttl_seconds
        self._timeout = settings.redis_timeout_seconds
        self.hits = 0
        self.misses = 0
        self.degraded = 0

    @staticmethod
    def _key(entity: str, entity_id: str) -> str:
        return f"oms:{entity}:{entity_id}"

    async def get(self, entity: str, entity_id: str) -> dict[str, Any] | None:
        try:
            raw = await asyncio.wait_for(
                self._redis.get(self._key(entity, entity_id)), timeout=self._timeout
            )
        except Exception:
            self.degraded += 1
            logger.warning("cache read degraded to miss", exc_info=True)
            return None
        if raw is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(raw)

    async def set(self, entity: str, entity_id: str, payload: dict[str, Any]) -> None:
        try:
            await asyncio.wait_for(
                self._redis.set(
                    self._key(entity, entity_id), json.dumps(payload, default=str), ex=self._ttl
                ),
                timeout=self._timeout,
            )
        except Exception:
            self.degraded += 1
            logger.warning("cache write skipped", exc_info=True)

    async def invalidate(self, entity: str, entity_id: str) -> None:
        """Called after every successful mutation so the copies cannot diverge."""
        try:
            await asyncio.wait_for(
                self._redis.delete(self._key(entity, entity_id)), timeout=self._timeout
            )
        except Exception:
            self.degraded += 1
            logger.warning("cache invalidation failed; entry will expire via TTL", exc_info=True)

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "degraded": self.degraded}
