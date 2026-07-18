from sqlalchemy import Column, String, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base
import enum

class RecoveryStatus(enum.Enum):
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class RecoveryLog(Base):
    __tablename__ = "recovery_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(Enum(RecoveryStatus), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())