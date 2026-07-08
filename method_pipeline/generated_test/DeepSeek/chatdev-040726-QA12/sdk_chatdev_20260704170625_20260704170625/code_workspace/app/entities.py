"""SQLAlchemy ORM entities — maps domain models to relational tables.

Uses String columns for enum fields to ensure portability across SQLite and PostgreSQL.
Values are stored as the enum's `.value` string.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain.models import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Customer ──────────────────────────────────────────────────────────────────
class CustomerEntity(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    banking_details: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.CUSTOMER.value, nullable=False
    )

    orders: Mapped[list["OrderEntity"]] = relationship(
        "OrderEntity", back_populates="customer", cascade="all, delete-orphan"
    )


# ── Product ───────────────────────────────────────────────────────────────────
class ProductEntity(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)


# ── Order ─────────────────────────────────────────────────────────────────────
class OrderEntity(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=OrderStatus.PENDING.value, nullable=False
    )
    invoice_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    customer: Mapped[CustomerEntity] = relationship(
        "CustomerEntity", back_populates="orders"
    )
    line_items: Mapped[list["LineItemEntity"]] = relationship(
        "LineItemEntity", back_populates="order", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["InvoiceEntity"]] = relationship(
        "InvoiceEntity", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[list["PaymentEntity"]] = relationship(
        "PaymentEntity", back_populates="order", cascade="all, delete-orphan"
    )


class LineItemEntity(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[OrderEntity] = relationship("OrderEntity", back_populates="line_items")
    product: Mapped["ProductEntity"] = relationship("ProductEntity")


# ── Payment ───────────────────────────────────────────────────────────────────
class PaymentEntity(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=PaymentStatus.PENDING.value, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    order: Mapped[OrderEntity] = relationship("OrderEntity", back_populates="payments")
    invoice: Mapped["InvoiceEntity"] = relationship("InvoiceEntity", back_populates="payments")


# ── Invoice ───────────────────────────────────────────────────────────────────
class InvoiceEntity(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False
    )
    billing_name: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_address: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=InvoiceStatus.DRAFT.value, nullable=False
    )

    order: Mapped[OrderEntity] = relationship("OrderEntity", back_populates="invoices")
    customer: Mapped[CustomerEntity] = relationship("CustomerEntity")
    payments: Mapped[list[PaymentEntity]] = relationship(
        "PaymentEntity", back_populates="invoice", cascade="all, delete-orphan"
    )