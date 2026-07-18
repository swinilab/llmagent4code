from sqlalchemy import Column, String, Float, Enum, DateTime, JSON
from sqlalchemy.sql import func
from .base import Base
import enum

class InvoiceStatus(enum.Enum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    billing_info = Column(JSON, nullable=False)
    total_amount = Column(Float, nullable=False)
    issue_date = Column(DateTime, server_default=func.now())
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.ISSUED)