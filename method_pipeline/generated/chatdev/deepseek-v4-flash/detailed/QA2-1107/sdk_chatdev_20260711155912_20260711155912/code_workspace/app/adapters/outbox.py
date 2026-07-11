"""
Transactional Outbox pattern for reliable state transition publishing (NFR 2.3).

When an order transitions state, we write an outbox message in the same
database transaction. A background worker polls the outbox table and
delivers messages to downstream handlers (e.g., analytics, notifications).

This ensures that state changes are never lost even if the process crashes
between writing the state and publishing the event.

NOTE: OutboxMessage uses the same Base metadata as all domain models
(app.domain.models.Base), so Alembic autogenerate can detect schema
changes to the outbox_messages table.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, Text, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.domain.models import Base
from app.infrastructure.retry import db_retry

logger = logging.getLogger(__name__)


class OutboxMessage(Base):
    """
    Outbox message stored in the same database as domain entities.

    Uses the same Base metadata (app.domain.models.Base) so that Alembic
    autogenerate detects this table and includes it in migrations.

    The `id`, `created_at`, `updated_at`, and `version` columns are
    inherited from Base.
    """
    __tablename__ = "outbox_messages"

    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OutboxRepository:
    """Repository for outbox messages with retry support for transient DB failures."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @db_retry
    async def add_message(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> OutboxMessage:
        """Add a message to the outbox within the current transaction."""
        message = OutboxMessage(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=json.dumps(payload, default=str),
        )
        self._session.add(message)
        await self._session.flush()
        return message

    @db_retry
    async def fetch_unprocessed(self, batch_size: int = 50) -> list[OutboxMessage]:
        """Fetch unprocessed messages for delivery."""
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.processed_at.is_(None))
            .order_by(OutboxMessage.created_at)
            .limit(batch_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    @db_retry
    async def mark_processed(self, message_id: uuid.UUID) -> None:
        """Mark a message as processed."""
        stmt = (
            update(OutboxMessage)
            .where(OutboxMessage.id == message_id)
            .values(processed_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)
        await self._session.flush()


class OutboxWorker:
    """
    Background worker that polls the outbox and delivers messages.

    In a single-node deployment, this runs as an asyncio task inside the
    application process. For production multi-node, this would be a
    separate process.
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._running = False

    async def process_messages(self) -> None:
        """Process one batch of outbox messages."""
        try:
            async with self._session_factory() as session:
                repo = OutboxRepository(session)
                messages = await repo.fetch_unprocessed(
                    batch_size=settings.OUTBOX_BATCH_SIZE
                )
                for msg in messages:
                    try:
                        # Deliver the message (in production, publish to a message broker)
                        payload = json.loads(msg.payload)
                        logger.info(
                            "Delivering outbox event: %s/%s (agg=%s, id=%s)",
                            msg.event_type,
                            payload.get("status", "?"),
                            msg.aggregate_type,
                            msg.aggregate_id,
                        )
                        await repo.mark_processed(msg.id)
                    except Exception as exc:
                        logger.error(
                            "Failed to process outbox message %s: %s",
                            msg.id,
                            exc,
                        )
                if messages:
                    await session.commit()
        except Exception as exc:
            logger.error("Outbox worker error: %s", exc)
