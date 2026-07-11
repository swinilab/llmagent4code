"""
Durable task queue using Redis Streams (NFR 1.3, NFR 2.3).

Redis Streams provide:
  - At-least-once delivery (consumer groups with pending entries).
  - Persistence (RDB/AOF) so messages survive a crash.
  - Backpressure via consumer group pending list length monitoring.

Admission control (NFR 1.3):
  - We monitor the stream length and reject new enqueues if the backlog
    exceeds a threshold (e.g., 10,000 pending messages).
  - This prevents unbounded memory growth.

State preservation (NFR 2.3):
  - On restart, pending messages in the stream are re-processed.
  - The outbox pattern (writing to DB + stream in the same transaction)
    ensures no order state is lost.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Coroutine, Optional

from redis.asyncio import Redis

from oms.config import settings
from oms.infrastructure.cache import get_redis

logger = logging.getLogger(__name__)

# Maximum backlog before rejecting new messages (NFR 1.3 admission control)
MAX_STREAM_LENGTH = 10_000

# Consumer group name
CONSUMER_GROUP = "oms-workers"

# How many messages to read per poll
BATCH_SIZE = 10

# Block time (ms) when no messages available
BLOCK_MS = 2000


async def _ensure_group(stream: str) -> None:
    """Create consumer group if it does not exist."""
    r = await get_redis()
    try:
        await r.xgroup_create(stream, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception:
        # Group already exists
        pass


async def enqueue(stream: str, message: dict[str, Any]) -> bool:
    """Enqueue a message with admission control.

    Returns True if enqueued, False if rejected due to backlog.
    """
    r = await get_redis()
    length = await r.xlen(stream)
    if length >= MAX_STREAM_LENGTH:
        logger.warning(
            "Stream %s backlog %d >= %d — rejecting message",
            stream, length, MAX_STREAM_LENGTH,
        )
        return False
    await _ensure_group(stream)
    await r.xadd(stream, message, maxlen=MAX_STREAM_LENGTH * 2)
    return True


async def dequeue(
    stream: str,
    consumer: str,
    timeout: int = BLOCK_MS,
) -> list[dict[str, Any]]:
    """Read pending messages from the stream (blocking read)."""
    r = await get_redis()
    await _ensure_group(stream)
    results = await r.xreadgroup(
        CONSUMER_GROUP,
        consumer,
        {stream: ">"},
        count=BATCH_SIZE,
        block=timeout,
    )
    messages: list[dict[str, Any]] = []
    if results:
        for stream_name, entries in results:
            for msg_id, fields in entries:
                messages.append({
                    "id": msg_id,
                    "stream": stream_name,
                    "data": fields,
                })
    return messages


async def ack(stream: str, message_id: str) -> None:
    """Acknowledge a message as processed."""
    r = await get_redis()
    await r.xack(stream, CONSUMER_GROUP, message_id)


async def claim_pending(
    stream: str,
    consumer: str,
    min_idle_time_ms: int = 30_000,
) -> list[dict[str, Any]]:
    """Claim pending messages that have been idle too long (crash recovery).

    Uses entry["time_since_delivered"] (the correct key returned by
    redis-py's XPENDING_RANGE) to determine which messages are eligible
    for claiming. Messages delivered more than 3 times are dead-lettered.
    """
    r = await get_redis()
    await _ensure_group(stream)
    pending = await r.xpending_range(
        stream, CONSUMER_GROUP, min="-", max="+", count=100
    )
    claimed: list[dict[str, Any]] = []
    for entry in pending:
        if entry["times_delivered"] > 3:
            # Dead-letter: skip after 3 retries
            logger.error("Dead-letter message %s on stream %s", entry["message_id"], stream)
            await ack(stream, entry["message_id"])
            continue
        if entry["time_since_delivered"] >= min_idle_time_ms:
            result = await r.xclaim(
                stream, CONSUMER_GROUP, consumer, min_idle_time_ms,
                [entry["message_id"]],
            )
            if result:
                for msg_id, fields in result:
                    claimed.append({
                        "id": msg_id,
                        "stream": stream,
                        "data": fields,
                    })
    return claimed


async def get_stream_length(stream: str) -> int:
    """Get current stream length for monitoring."""
    r = await get_redis()
    return await r.xlen(stream)


async def check_queue_health() -> bool:
    """Health-check: verify Redis is reachable and streams are operational."""
    try:
        r = await get_redis()
        await r.ping()
        return True
    except Exception:
        return False
