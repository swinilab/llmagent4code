from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from aiolimiter import AsyncLimiter
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.resilience import DependencyTimeoutError, run_with_timeout
from app.core.observability import OUTBOX_DEFERRED, OUTBOX_PUBLISHED
from app.db.models import OutboxEventModel
from app.repositories.outbox_repository import OutboxRepository


logger = logging.getLogger(__name__)


def _event_json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (UUID, date, datetime)):
        return value.isoformat() if not isinstance(value, UUID) else str(value)
    if isinstance(value, Enum):
        return str(value.value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


class OutboxDispatcher:
    """Publishes committed events at a bounded rate with at-least-once delivery."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: Redis,
        *,
        stream_name: str,
        max_rate: int,
        batch_size: int,
        poll_interval_seconds: float,
        dependency_timeout_seconds: float,
        stream_maxlen: int = 100_000,
    ) -> None:
        if max_rate <= 0 or batch_size <= 0:
            raise ValueError("max_rate and batch_size must be greater than zero")
        if poll_interval_seconds <= 0 or dependency_timeout_seconds <= 0:
            raise ValueError("poll and dependency timeouts must be greater than zero")
        if stream_maxlen <= 0:
            raise ValueError("stream_maxlen must be greater than zero")
        self._session_factory = session_factory
        self._redis = redis
        self._stream_name = stream_name
        self._batch_size = batch_size
        self._poll_interval_seconds = poll_interval_seconds
        self._dependency_timeout_seconds = dependency_timeout_seconds
        self._stream_maxlen = stream_maxlen
        self._limiter = AsyncLimiter(max_rate=max_rate, time_period=1.0)
        self._dispatch_lock = asyncio.Lock()

    async def dispatch_pending_events(self) -> int:
        """Publish one locked batch and leave failed rows durable for retry."""

        published = 0
        async with self._dispatch_lock:
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        repository = OutboxRepository(session)
                        events = await repository.claim_batch(self._batch_size)
                        for event in events:
                            async with self._limiter:
                                try:
                                    await self._publish(event)
                                except (DependencyTimeoutError, RedisError, OSError) as exc:
                                    repository.mark_failed(event, exc)
                                    OUTBOX_DEFERRED.inc()
                                    logger.warning(
                                        "event transport unavailable; outbox event retained",
                                        extra={"event_id": str(event.id)},
                                    )
                                    break
                                repository.mark_published(event)
                                OUTBOX_PUBLISHED.inc()
                                published += 1
            except SQLAlchemyError:
                logger.exception("outbox dispatch database transaction failed")
                return 0
        return published

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        stop_event = stop_event or asyncio.Event()
        while not stop_event.is_set():
            try:
                published = await self.dispatch_pending_events()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("unexpected outbox dispatcher failure")
                published = 0
            if published < self._batch_size:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=self._poll_interval_seconds
                    )
                except TimeoutError:
                    pass

    async def _publish(self, event: OutboxEventModel) -> None:
        values = {
            "event_id": str(event.id),
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id),
            "event_type": event.event_type,
            "created_at": event.created_at.isoformat(),
            "payload": json.dumps(
                event.payload,
                default=_event_json_default,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        }
        await run_with_timeout(
            self._redis.xadd(
                self._stream_name,
                values,
                maxlen=self._stream_maxlen,
                approximate=True,
            ),
            self._dependency_timeout_seconds,
            dependency="redis event stream",
        )
