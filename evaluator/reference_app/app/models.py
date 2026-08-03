"""Domain entities.

Only what the six scenarios and the seven-step workflow require. Field-level
validation is intentionally light: this application calibrates the tactic
scenarios, and reproducing the full constraint table would amount to doing the
generation task rather than checking the instrument that measures it.

Money is stored as Numeric(12, 2), never as a float, because ASR-A4 compares
persisted amounts for exact equality and binary floating point would make that
comparison unreliable in a way unrelated to the tactic.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    DateTime,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(16))
    account_number: Mapped[str] = mapped_column(String(20))
    bank_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="CUSTOMER")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    description: Mapped[str] = mapped_column(String(500))
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    price_currency: Mapped[str] = mapped_column(String(3))


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    customer_ref: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"))
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="PLACED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    invoice_ref: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id"))
    product_ref: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(12, 2))

    order: Mapped[Order] = relationship(back_populates="line_items")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    order_ref: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id"))
    billing_name: Mapped[str] = mapped_column(String(100))
    billing_address: Mapped[str] = mapped_column(String(255))
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="ISSUED")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    order_ref: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    method: Mapped[str] = mapped_column(String(20))
