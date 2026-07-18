"""Order entity with full lifecycle status enum."""

from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, _new_uuid


class OrderStatus(str, enum.Enum):
    """Full order lifecycle."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Order(Base, TimestampMixin):
    """Customer order with line items, amounts, and status."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    customer_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("customers.id"), nullable=False, index=True
    )
    line_items: Mapped[str] = mapped_column(Text, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING
    )
    invoice_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    customer = relationship("Customer", back_populates="orders")
    payments = relationship("Payment", back_populates="order", lazy="selectin")
    invoice = relationship("Invoice", back_populates="order", uselist=False, lazy="selectin")

    def __repr__(self) -> str:
        return f"<Order id={self.id!r} status={self.status.value!r}>"
