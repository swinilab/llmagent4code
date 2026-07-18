from sqlalchemy import Column, String, JSON, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class Outbox(Base):
    __tablename__ = "outbox"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    processed = Column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint('event_type', 'entity_id', name='uq_event_entity'),
    )