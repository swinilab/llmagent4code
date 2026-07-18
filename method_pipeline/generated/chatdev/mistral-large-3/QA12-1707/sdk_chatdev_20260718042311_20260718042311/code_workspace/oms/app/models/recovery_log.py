"""
Recovery log model for pending orders, invoices, and payments.
"""
from sqlalchemy import Column, String, JSON, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from app.db.base import Base


class RecoveryLog(Base):
    """Recovery log for pending orders, invoices, and payments."""
    __tablename__ = "recovery_log"

    id = Column(String, primary_key=True)
    aggregate_type = Column(String, nullable=False)  # "ORDER", "INVOICE", "PAYMENT"
    aggregate_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    checkpoint_data = Column(JSON, nullable=False)
    is_recovered = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RecoveryLog(id={self.id}, aggregate_type={self.aggregate_type}, status={self.status})>"