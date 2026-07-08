"""
Invoice ORM model.
"""
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship

from app.database import Base
import enum


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    billing_info = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(SAEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    issue_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    order = relationship("Order", back_populates="invoices")

    def __repr__(self) -> str:
        return f"<Invoice {self.id} status={self.status}>"
