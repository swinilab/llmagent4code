from sqlalchemy import Column, String, JSON, Enum, Float, DateTime, Boolean
from sqlalchemy.sql import func
from .base import Base
import enum

class OrderStatus(enum.Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False)
    line_items = Column(JSON, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PLACED)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    invoice_id = Column(String, nullable=True)
    is_pending_recovery = Column(Boolean, default=False)