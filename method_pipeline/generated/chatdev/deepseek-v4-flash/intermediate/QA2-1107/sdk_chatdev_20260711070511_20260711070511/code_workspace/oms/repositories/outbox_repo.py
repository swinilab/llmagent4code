"""
Outbox repository for replaying pending messages on restart (NFR 2.3).

Includes retry logic for failed messages (NFR 2.2 – Fault Detection and Recovery).
"""
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from oms.models.entities import OutboxMessage
from oms.models.enums import OutboxStatus
from oms.repositories.base import BaseRepository

# Maximum number of retries for a failed outbox message
MAX_OUTBOX_RETRY_COUNT = 5


class OutboxRepository(BaseRepository[OutboxMessage]):
    def __init__(self, db: Session):
        super().__init__(OutboxMessage, db)

    def get_pending(self, limit: int = 50) -> List[OutboxMessage]:
        """
        Fetch messages that need processing:
        - PENDING messages (never attempted)
        - FAILED messages with retry_count below MAX_OUTBOX_RETRY_COUNT
        """
        return (
            self.db.query(OutboxMessage)
            .filter(
                (OutboxMessage.status == OutboxStatus.PENDING)
                | (
                    (OutboxMessage.status == OutboxStatus.FAILED)
                    & (OutboxMessage.retry_count < MAX_OUTBOX_RETRY_COUNT)
                )
            )
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    def mark_processed(self, message_id: str) -> None:
        self.db.query(OutboxMessage).filter(
            OutboxMessage.id == message_id
        ).update({
            "status": OutboxStatus.PROCESSED,
            "processed_at": datetime.now(timezone.utc),
        })
        self.db.flush()

    def mark_failed(self, message_id: str) -> None:
        """
        Mark a message as FAILED and increment its retry_count.
        The next poll cycle will re-attempt it (up to MAX_OUTBOX_RETRY_COUNT times).
        """
        self.db.query(OutboxMessage).filter(
            OutboxMessage.id == message_id
        ).update({
            "status": OutboxStatus.FAILED,
            "retry_count": OutboxMessage.retry_count + 1,
        })
        self.db.flush()
