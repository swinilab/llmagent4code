"""Idempotency handling for payment submission (NFR 1.3).

Strategy: Store idempotency keys in Redis with a TTL.
  - On first request: store key → response, process normally.
  - On retry with same key: return stored response without reprocessing.
  - TTL: 24 hours (configurable) — covers the spike window and retry horizon.

This makes payment retries safe under spike conditions: if a client retries
a payment submission due to timeout, the duplicate is detected and the
original result is returned.
"""

import json
from typing import Any, Optional

from app.config import settings
import app.infrastructure.cache as cache


def _idempotency_key(key: str) -> str:
    return f"idempotency:{key}"


async def get_idempotent_response(key: str) -> Optional[dict[str, Any]]:
    """Get a previously stored response for an idempotency key.

    Args:
        key: The idempotency key from the request header.

    Returns:
        The stored response dict, or None if not found.
    """
    if cache.redis_client is None:
        return None
    data = await cache.redis_client.get(_idempotency_key(key))
    if data is None:
        return None
    return json.loads(data)


async def store_idempotent_response(key: str, response: dict[str, Any]) -> None:
    """Store a response for an idempotency key with TTL.

    Args:
        key: The idempotency key.
        response: The response dict to store.
    """
    if cache.redis_client is None:
        return
    await cache.redis_client.setex(
        _idempotency_key(key),
        settings.idempotency_ttl_seconds,
        json.dumps(response, default=str),
    )
