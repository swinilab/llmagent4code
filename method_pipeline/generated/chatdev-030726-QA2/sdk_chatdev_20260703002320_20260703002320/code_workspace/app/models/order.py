"""
SQLAlchemy model for Order.
"""

from sqlalchemy import Column, Integer, ForeignKey, Enum, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db import Base

class OrderStatus(str, enum.Enum):
    PLACED = "placed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PLACED)
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    customer = relationship("Customer")
    line_items = relationship("OrderLineItem", cascade="all, delete-orphan")
    invoice = relationship("Invoice", uselist=False)
