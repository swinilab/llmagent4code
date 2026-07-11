"""
SQLAlchemy ORM models - database representation of the domain.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings
from app.domain import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


def utcnow() -> datetime:
    """Return current UTC datetime (replacement for deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(_uuid.uuid4())


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    banking_details: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"), default=UserRole.CUSTOMER
    )

    orders: Mapped[list["OrderModel"]] = relationship(
        "OrderModel", back_populates="customer", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    description: Mapped[str] = mapped_column(Text, default="")
    base_price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum"),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    invoice_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    customer: Mapped[CustomerModel] = relationship(
        "CustomerModel", back_populates="orders"
    )
    line_items: Mapped[list["LineItemModel"]] = relationship(
        "LineItemModel", back_populates="order", cascade="all, delete-orphan"
    )


class LineItemModel(Base):
    __tablename__ = "line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    order: Mapped[OrderModel] = relationship("OrderModel", back_populates="line_items")


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum"),
        default=PaymentMethod.CREDIT_CARD,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        default=PaymentStatus.PENDING,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
class InvoiceModel(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    billing_name: Mapped[str] = mapped_column(String(255), default="")
    billing_address: Mapped[str] = mapped_column(Text, default="")
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    issue_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    due_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status_enum"),
        default=InvoiceStatus.DRAFT,
    )


# ---------------------------------------------------------------------------
# Event log for state preservation
# ---------------------------------------------------------------------------
class EventLogModel(Base):
    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# ---- Enforce foreign key constraints in SQLite ----
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
# ---------------------------------------------------


def init_db():
    """Create all tables. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine)
