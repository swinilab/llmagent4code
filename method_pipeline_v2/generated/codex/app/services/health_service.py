from __future__ import annotations

from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.observability import DEPENDENCY_UP
from app.core.resilience import DependencyTimeoutError, run_with_timeout
from app.repositories.outbox_repository import OutboxRepository


class HealthService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: Redis,
        *,
        timeout_seconds: float,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis
        self._timeout_seconds = timeout_seconds

    async def check(self) -> dict[str, Any]:
        database_ok = False
        redis_ok = False
        pending_events: int | None = None

        try:
            async with self._session_factory() as session:
                await run_with_timeout(
                    session.execute(text("SELECT 1")),
                    self._timeout_seconds,
                    dependency="postgresql health probe",
                )
                pending_events = await run_with_timeout(
                    OutboxRepository(session).pending_count(),
                    self._timeout_seconds,
                    dependency="postgresql outbox probe",
                )
                database_ok = True
        except (DependencyTimeoutError, SQLAlchemyError, OSError):
            database_ok = False

        try:
            redis_ok = bool(
                await run_with_timeout(
                    self._redis.ping(),
                    self._timeout_seconds,
                    dependency="redis health probe",
                )
            )
        except (DependencyTimeoutError, RedisError, OSError):
            redis_ok = False

        DEPENDENCY_UP.labels("postgresql").set(1 if database_ok else 0)
        DEPENDENCY_UP.labels("redis").set(1 if redis_ok else 0)
        status = "ready" if database_ok and redis_ok else "degraded" if database_ok else "unavailable"
        return {
            "status": status,
            "criticalReady": database_ok,
            "dependencies": {
                "postgresql": "up" if database_ok else "down",
                "redis": "up" if redis_ok else "down",
            },
            "pendingOutboxEvents": pending_events,
        }

