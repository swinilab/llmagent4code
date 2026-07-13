from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timedelta
import enum


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    billing_info = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="invoice")