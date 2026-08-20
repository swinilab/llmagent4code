from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.resilience import DependencyTimeoutError, run_with_timeout
from app.core.observability import CACHE_FAILURES


logger = logging.getLogger(__name__)


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


class EntityCache:
    """Fail-open Redis secondary copy containing versioned entity snapshots."""

    def __init__(
        self,
        redis: Redis,
        *,
        ttl_seconds: int,
        timeout_seconds: float,
        key_prefix: str = "oms:entity",
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._redis = redis
        self._ttl_seconds = ttl_seconds
        self._timeout_seconds = timeout_seconds
        self._key_prefix = key_prefix.rstrip(":")

    @staticmethod
    def payload_checksum(payload: dict[str, Any]) -> str:
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    def key_for(self, entity_type: str, entity_id: UUID | str) -> str:
        normalized_type = entity_type.strip().lower()
        if not normalized_type or ":" in normalized_type or "*" in normalized_type:
            raise ValueError("entity_type must be a non-empty cache-key segment")
        return f"{self._key_prefix}:{normalized_type}:{entity_id}"

    async def get_json(
        self,
        entity_type: str,
        entity_id: UUID | str,
    ) -> dict[str, Any] | None:
        """Return a verified cached payload, or a miss when Redis is unavailable."""

        key = self.key_for(entity_type, entity_id)
        try:
            raw = await run_with_timeout(
                self._redis.get(key),
                self._timeout_seconds,
                dependency="redis cache read",
            )
        except (DependencyTimeoutError, RedisError, OSError):
            CACHE_FAILURES.labels("read").inc()
            logger.warning("cache read failed; using canonical store", exc_info=True)
            return None
        if raw is None:
            return None
        try:
            envelope = self._decode_envelope(raw)
            payload = envelope["payload"]
            if envelope["checksum"] != self.payload_checksum(payload):
                logger.warning("cache checksum mismatch for %s", key)
                return None
            return payload
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning("invalid cache envelope for %s", key, exc_info=True)
            return None

    async def get_envelope(
        self,
        entity_type: str,
        entity_id: UUID | str,
    ) -> dict[str, Any] | None:
        """Return an envelope for reconciliation without trusting its checksum."""

        key = self.key_for(entity_type, entity_id)
        try:
            raw = await run_with_timeout(
                self._redis.get(key),
                self._timeout_seconds,
                dependency="redis cache reconciliation read",
            )
        except (DependencyTimeoutError, RedisError, OSError):
            CACHE_FAILURES.labels("reconciliation_read").inc()
            logger.warning("cache reconciliation read failed", exc_info=True)
            return None
        if raw is None:
            return None
        try:
            return self._decode_envelope(raw)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning("invalid cache envelope for %s", key, exc_info=True)
            return None

    async def set_json(
        self,
        entity_type: str,
        entity_id: UUID | str,
        payload: dict[str, Any],
        *,
        version: int | str | None = None,
    ) -> bool:
        """Write the Redis copy and report failure without failing canonical work."""

        key = self.key_for(entity_type, entity_id)
        envelope = {
            "entityType": entity_type.strip().lower(),
            "entityId": str(entity_id),
            "version": version,
            "checksum": self.payload_checksum(payload),
            "cachedAt": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        try:
            stored = await run_with_timeout(
                self._redis.set(
                    key,
                    _canonical_json(envelope),
                    ex=self._ttl_seconds,
                ),
                self._timeout_seconds,
                dependency="redis cache write",
            )
            return bool(stored)
        except (DependencyTimeoutError, RedisError, OSError):
            CACHE_FAILURES.labels("write").inc()
            logger.warning("cache write failed; canonical commit remains valid", exc_info=True)
            return False

    async def invalidate(self, entity_type: str, entity_id: UUID | str) -> bool:
        key = self.key_for(entity_type, entity_id)
        try:
            await run_with_timeout(
                self._redis.delete(key),
                self._timeout_seconds,
                dependency="redis cache invalidation",
            )
            return True
        except (DependencyTimeoutError, RedisError, OSError):
            CACHE_FAILURES.labels("invalidation").inc()
            logger.warning("cache invalidation failed", exc_info=True)
            return False

    async def list_entity_ids(self, entity_type: str, *, scan_count: int = 500) -> set[str]:
        """List secondary-copy IDs in bounded Redis SCAN calls."""

        if scan_count <= 0:
            raise ValueError("scan_count must be greater than zero")
        prefix = self.key_for(entity_type, "")
        cursor: int | str | bytes = 0
        entity_ids: set[str] = set()
        try:
            while True:
                cursor, keys = await run_with_timeout(
                    self._redis.scan(
                        cursor=cursor,
                        match=f"{prefix}*",
                        count=scan_count,
                    ),
                    self._timeout_seconds,
                    dependency="redis cache scan",
                )
                for raw_key in keys:
                    key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else str(raw_key)
                    entity_ids.add(key.removeprefix(prefix))
                if cursor in (0, "0", b"0"):
                    break
        except (DependencyTimeoutError, RedisError, OSError):
            CACHE_FAILURES.labels("scan").inc()
            logger.warning("cache scan failed", exc_info=True)
            return set()
        return entity_ids

    @staticmethod
    def _decode_envelope(raw: bytes | str) -> dict[str, Any]:
        decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        envelope = json.loads(decoded)
        if not isinstance(envelope, dict):
            raise TypeError("cache envelope must be an object")
        payload = envelope["payload"]
        if not isinstance(payload, dict):
            raise TypeError("cache payload must be an object")
        if not isinstance(envelope["checksum"], str):
            raise TypeError("cache checksum must be a string")
        return envelope
