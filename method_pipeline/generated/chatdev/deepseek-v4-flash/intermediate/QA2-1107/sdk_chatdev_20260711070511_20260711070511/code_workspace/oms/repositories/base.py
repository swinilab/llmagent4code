"""
Base repository with common CRUD operations and optimistic-locking update.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from oms.models.entities import OutboxMessage, OutboxStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic repository with shared CRUD and outbox helpers."""

    def __init__(self, model_class: Type[T], db: Session):
        self.model_class = model_class
        self.db = db

    def get(self, entity_id: str) -> Optional[T]:
        return self.db.query(self.model_class).filter(
            self.model_class.id == entity_id
        ).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        return self.db.query(self.model_class).offset(skip).limit(limit).all()

    def create(self, entity: T) -> T:
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity_id: str) -> bool:
        obj = self.get(entity_id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True

    def update_with_optimistic_lock(
        self, entity_id: str, updates: Dict[str, Any], current_version: int
    ) -> Optional[T]:
        """
        UPDATE … SET version = version + 1, … WHERE id = :id AND version = :v
        Returns the updated row or None if version mismatch.
        """
        stmt = (
            self.model_class.__table__.update()
            .where(self.model_class.id == entity_id)
            .where(self.model_class.version == current_version)
            .values(**updates, version=current_version + 1,
                    updated_at=datetime.now(timezone.utc))
        )
        result = self.db.execute(stmt)
        if result.rowcount == 0:
            logger.warning(
                "Optimistic lock failed for %s id=%s version=%d",
                self.model_class.__name__, entity_id, current_version,
            )
            return None
        self.db.flush()
        return self.get(entity_id)

    # ------------------------------------------------------------------
    # Transactional outbox helpers (NFR 2.3)
    # ------------------------------------------------------------------
    def write_outbox(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> OutboxMessage:
        """Persist an outbox message in the current transaction."""
        msg = OutboxMessage(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=json.dumps(payload, default=str),
        )
        self.db.add(msg)
        self.db.flush()
        return msg
