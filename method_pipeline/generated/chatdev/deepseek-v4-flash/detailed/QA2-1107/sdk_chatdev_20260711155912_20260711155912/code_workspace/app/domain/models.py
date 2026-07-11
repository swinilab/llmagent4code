"""
SQLAlchemy ORM models for the Order Management System.

Every entity includes an optimistic-lock version field (version) and
timestamps for auditability.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    Currency,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


class Base(DeclarativeBase):
    """Abstract base with common audit columns."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    banking_details: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", create_constraint=True),
        default=UserRole.CUSTOMER,
        nullable=False,
    )

    orders = relationship("Order", back_populates="customer", lazy="selectin")


class Product(Base):
    __tablename__ = "products"

    description: Mapped[str] = mapped_column(Text, nullable=False)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency_enum", create_constraint=True),
        default=Currency.USD,
        nullable=False,
    )
    available: Mapped[bool] = mapped_column(default=True, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum", create_constraint=True),
        default=OrderStatus.CREATED,
        nullable=False,
    )
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency_enum", create_constraint=True),
        default=Currency.USD,
        nullable=False,
    )
    invoice_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepted_at_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invoiced_at_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shipped_at_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer = relationship("Customer", back_populates="orders", lazy="selectin")
    line_items = relationship("OrderLineItem", back_populates="order", lazy="selectin")
    payments = relationship("Payment", back_populates="order", lazy="selectin")
    invoices = relationship("Invoice", back_populates="order", lazy="selectin")


class OrderLineItem(Base):
    __tablename__ = "order_line_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency_enum", create_constraint=True),
        default=Currency.USD,
        nullable=False,
    )

    order = relationship("Order", back_populates="line_items")
    product = relationship("Product", lazy="selectin")


class Payment(Base):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", create_constraint=True),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", create_constraint=True),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    order = relationship("Order", back_populates="payments")


class Invoice(Base):
    __tablename__ = "invoices"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    billing_info: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency_enum", create_constraint=True),
        default=Currency.USD,
        nullable=False,
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status_enum", create_constraint=True),
        default=InvoiceStatus.DRAFT,
        nullable=False,
    )

    order = relationship("Order", back_populates="invoices")
