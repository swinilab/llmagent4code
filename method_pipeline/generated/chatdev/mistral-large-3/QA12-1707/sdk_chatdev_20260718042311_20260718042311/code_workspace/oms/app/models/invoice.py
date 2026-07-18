"""
Invoice domain model.
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class InvoiceStatus(str, Enum):
    """Invoice status lifecycle."""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(Base):
    """Invoice domain model."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    billing_info = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    issue_date = Column(DateTime, server_default=func.now(), nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)

    order = relationship("Order", back_populates="invoice")