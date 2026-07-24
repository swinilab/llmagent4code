"""
SQLAlchemy ORM entities for the OMS domain model.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship

from app.database import Base
from app.models.enums import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(32), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(50), nullable=False)
    banking_details = Column(Text, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    orders = relationship("Order", back_populates="customer", lazy="selectin")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(32), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    base_price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    stock_quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    order_items = relationship("OrderItem", back_populates="product", lazy="selectin")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(32), primary_key=True, default=_uuid)
    customer_id = Column(String(32), ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    total_amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    customer = relationship("Customer", back_populates="orders", lazy="selectin")
    line_items = relationship("OrderItem", back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False, lazy="selectin")
    invoice = relationship("Invoice", back_populates="order", uselist=False, lazy="selectin")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(32), primary_key=True, default=_uuid)
    order_id = Column(String(32), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(32), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="line_items", lazy="selectin")
    product = relationship("Product", back_populates="order_items", lazy="selectin")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_payments_order_id"),
    )

    id = Column(String(32), primary_key=True, default=_uuid)
    order_id = Column(String(32), ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    transaction_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    order = relationship("Order", back_populates="payment", lazy="selectin")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(32), primary_key=True, default=_uuid)
    order_id = Column(String(32), ForeignKey("orders.id"), nullable=False, unique=True)
    customer_id = Column(String(32), ForeignKey("customers.id"), nullable=False)
    billing_info = Column(Text, nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    issue_date = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    due_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    order = relationship("Order", back_populates="invoice", lazy="selectin")
    customer = relationship("Customer", lazy="selectin")
