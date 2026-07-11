"""
Order and OrderLineItem ORM models.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import String, DateTime, Numeric, ForeignKey, Enum, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import OrderStatus


class OrderLineItem(Base):
    __tablename__ = "order_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    product_description: Mapped[str] = mapped_column(String(1000), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="line_items")

    def __repr__(self) -> str:
        return f"<OrderLineItem {self.id} qty={self.quantity}>"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    invoice_ref: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="orders", lazy="selectin")
    line_items: Mapped[List[OrderLineItem]] = relationship(
        "OrderLineItem", back_populates="order", lazy="selectin", cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="order", lazy="selectin")
    invoices = relationship("Invoice", back_populates="order", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Order {self.id} status={self.status}>"
