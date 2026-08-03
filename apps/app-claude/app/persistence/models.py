"""SQLAlchemy 2.x ORM mapping.

Money is stored as NUMERIC(12, 2) and handled as `decimal.Decimal` end to end;
binary floating point is never used for persisted amounts.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    Currency,
    CustomerRole,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    bank_account_number: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[CustomerRole] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer", lazy="selectin")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_currency: Mapped[Currency] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint("price_amount > 0", name="ck_products_price_positive"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(String(16), nullable=False, default=OrderStatus.PLACED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="orders", lazy="selectin")
    line_items: Mapped[list["OrderLineItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderLineItem(Base):
    __tablename__ = "order_line_items"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="line_items")

    __table_args__ = (
        # Duplicate productRef within one order is rejected at the API layer with
        # 400; this constraint is the defence in depth behind that rule.
        UniqueConstraint("order_id", "product_id", name="uq_order_line_items_order_product"),
        CheckConstraint("quantity >= 1 AND quantity <= 1000", name="ck_line_items_quantity_range"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, unique=True
    )
    billing_name: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_address: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(String(16), nullable=False, default=InvoiceStatus.ISSUED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint("due_date >= issue_date", name="ck_invoices_due_after_issue"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    status: Mapped[PaymentStatus] = mapped_column(String(16), nullable=False, default=PaymentStatus.PENDING)
    method: Mapped[PaymentMethod] = mapped_column(String(16), nullable=False)
