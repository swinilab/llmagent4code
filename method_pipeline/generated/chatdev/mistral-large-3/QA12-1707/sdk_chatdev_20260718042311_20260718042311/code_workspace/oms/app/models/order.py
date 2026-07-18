"""
Order domain model.
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class OrderStatus(str, Enum):
    """Order status lifecycle."""
    PLACED = "placed"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"


class Order(Base):
    """Order domain model."""
    __tablename__ = "orders"
class Order(Base):
    """Order domain model."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PLACED, nullable=False)
    is_pending_recovery = Column(Boolean, default=True, nullable=False)  # Default to True for recovery
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    customer = relationship("Customer", back_populates="orders")
    line_items = relationship("OrderLineItem", back_populates="order")
    invoice = relationship("Invoice", back_populates="order", uselist=False)
    payment = relationship("Payment", back_populates="order", uselist=False)