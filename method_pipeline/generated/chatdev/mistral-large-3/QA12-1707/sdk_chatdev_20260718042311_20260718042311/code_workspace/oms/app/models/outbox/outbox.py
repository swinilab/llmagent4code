"""
Outbox model for event sourcing and recovery.
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from uuid import uuid4
from app.db.base import Base


class Outbox(Base):
    """Outbox model for persisting pending events."""
    __tablename__ = "outbox"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()), unique=True)
    event_type = Column(String, nullable=False)  # e.g., "ORDER_PLACED", "PAYMENT_PROCESSED", "INVOICE_GENERATED"
    payload = Column(JSON, nullable=False)       # Serialized event data
    processed = Column(Boolean, default=False, nullable=False)  # Whether the event has been processed
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class RecoveryLog(Base):
    """Recovery log to track processed events during recovery."""
    __tablename__ = "recovery_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()), unique=True)
    event_id = Column(String, nullable=False)  # Reference to Outbox.id
    status = Column(String, nullable=False, default="PENDING")  # PENDING, PROCESSED, FAILED