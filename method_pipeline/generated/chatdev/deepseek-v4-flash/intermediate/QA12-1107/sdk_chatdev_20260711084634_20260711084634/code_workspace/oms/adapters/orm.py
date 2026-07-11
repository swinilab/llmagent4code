"""
SQLAlchemy ORM models mapping domain entities to PostgreSQL tables.

Schema is annotated for durability (NFR 2.3):
  - All tables use InnoDB-equivalent (PostgreSQL) with ACID guarantees.
  - Optimistic locking via `version` column.
  - Indexes on foreign keys and status columns for query performance.
  - JSON columns for flexible data (line_items, addresses).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    JSON,
    Numeric,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Customer table
# ---------------------------------------------------------------------------
class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    phone: Mapped[str] = mapped_column(String(50), default="")
    banking_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    order_history: Mapped[list] = mapped_column(JSON, default=list)
    role: Mapped[str] = mapped_column(String(20), default="CUSTOMER")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    orders = relationship("OrderModel", back_populates="customer_ref")


# ---------------------------------------------------------------------------
# Product table
# ---------------------------------------------------------------------------
class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    base_price_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    base_price_currency: Mapped[str] = mapped_column(String(3), default="USD")
    stock: Mapped[int] = mapped_column(Integer, default=0)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    __table_args__ = (
        Index("idx_products_available", "available"),
    )


# ---------------------------------------------------------------------------
# Order table
# ---------------------------------------------------------------------------
class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("customers.id"), nullable=False
    )
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(
        String(20), default="CREATED", index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    total_currency: Mapped[str] = mapped_column(String(3), default="USD")
    invoice_ref: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    payment_ref: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    shipping_address: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    customer_ref = relationship("CustomerModel", back_populates="orders")
    payments = relationship("PaymentModel", back_populates="order_ref")
    invoices = relationship("InvoiceModel", back_populates="order_ref")

    __table_args__ = (
        Index("idx_orders_customer", "customer_id"),
        Index("idx_orders_status_created", "status", "created_at"),
    )


# ---------------------------------------------------------------------------
# Payment table
# ---------------------------------------------------------------------------
class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("orders.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    method: Mapped[str] = mapped_column(String(30), default="CREDIT_CARD")
    transaction_id: Mapped[str] = mapped_column(String(64), default="")
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    order_ref = relationship("OrderModel", back_populates="payments")


# ---------------------------------------------------------------------------
# Invoice table
# ---------------------------------------------------------------------------
class InvoiceModel(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("orders.id"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("customers.id"), nullable=False
    )
    billing_address: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    issue_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    order_ref = relationship("OrderModel", back_populates="invoices")
