"""
SQLAlchemy model for Invoice.
"""
from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, Enum, String
from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, Enum
from datetime import datetime
import enum
from app.db import Base

class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    billing_info = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
