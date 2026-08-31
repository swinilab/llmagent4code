from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEventModel


class OutboxRepository:
    """Persists and locks transactional-outbox records using the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(
        self,
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        event_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> OutboxEventModel:
        event = OutboxEventModel(
            id=event_id or uuid4(),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            created_at=created_at or datetime.now(UTC),
            attempts=0,
        )
        self._session.add(event)
        return event

    async def claim_batch(self, limit: int) -> list[OutboxEventModel]:
        """Lock a bounded unpublished batch; the surrounding transaction owns the claim."""

        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        statement = (
            select(OutboxEventModel)
            .where(OutboxEventModel.published_at.is_(None))
            .order_by(OutboxEventModel.created_at, OutboxEventModel.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    def mark_published(
        self,
        event: OutboxEventModel,
        *,
        published_at: datetime | None = None,
    ) -> None:
        event.attempts += 1
        event.published_at = published_at or datetime.now(UTC)
        event.last_error = None

    def mark_failed(self, event: OutboxEventModel, error: BaseException | str) -> None:
        event.attempts += 1
        event.last_error = str(error)[:2_000]

    async def pending_count(self) -> int:
        statement = select(func.count()).select_from(OutboxEventModel).where(
            OutboxEventModel.published_at.is_(None)
        )
        return int((await self._session.scalar(statement)) or 0)

