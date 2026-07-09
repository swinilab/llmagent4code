"""
SQLAlchemy ORM models for the OMS domain.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
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


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    banking_details: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[CustomerRole] = mapped_column(
        Enum(CustomerRole, name="customer_role_enum", create_constraint=True),
        default=CustomerRole.CUSTOMER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    orders: Mapped[List[Order]] = relationship(
        "Order", back_populates="customer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    stock_available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} desc={self.description[:30]!r}>"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class Order(Base):
    __tablename__ = "orders"
    __mapper_args__ = {"version_id_col": "version"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum", create_constraint=True),
        default=OrderStatus.CREATED,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    customer: Mapped[Customer] = relationship("Customer", back_populates="orders")
    line_items: Mapped[List[OrderLineItem]] = relationship(
        "OrderLineItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List[Payment]] = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )
    invoices: Mapped[List[Invoice]] = relationship(
        "Invoice", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status}>"


class OrderLineItem(Base):
    __tablename__ = "order_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="line_items")
    product: Mapped[Product] = relationship("Product")

    def __repr__(self) -> str:
        return f"<LineItem id={self.id} product={self.product_id} qty={self.quantity}>"


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", create_constraint=True),
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", create_constraint=True),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    order: Mapped[Order] = relationship("Order", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} status={self.status}>"


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    billing_name: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_address: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status_enum", create_constraint=True),
        default=InvoiceStatus.DRAFT,
        nullable=False,
    )
    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    order: Mapped[Order] = relationship("Order", back_populates="invoices")

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} status={self.status}>"
