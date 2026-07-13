from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime
import enum


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_number = Column(String, unique=True, index=True, nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(OrderStatusEnum), default=OrderStatusEnum.PENDING, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)
    invoice = relationship("Invoice", back_populates="order", uselist=False)