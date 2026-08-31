"""SQLAlchemy ORM schema.

Money is NUMERIC(10,2)/(12,2) - never float - so the 2dp guarantee that the
DTOs enforce survives the round-trip to storage.

`version` columns give every mutable aggregate optimistic locking, which is how
concurrent workflow transitions are kept isolated (NFR 2.4 Transactions).
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now() -> datetime:
    return datetime.now(UTC)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    account_number: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer", lazy="selectin")

    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 2 AND 100", name="ck_customer_name_len"),
        CheckConstraint("char_length(address) BETWEEN 5 AND 255", name="ck_customer_addr_len"),
        CheckConstraint("role IN ('CUSTOMER','ORDER_STAFF','ACCOUNTANT')", name="ck_customer_role"),
        Index("ix_customers_deleted", "deleted"),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = _uuid_pk()
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        CheckConstraint("price_amount BETWEEN 0.01 AND 999999.99", name="ck_product_price_range"),
        CheckConstraint("price_currency IN ('USD','VND','EUR')", name="ck_product_currency"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = _uuid_pk()
    customer_ref: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PLACED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    invoice_ref: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    customer: Mapped[Customer] = relationship(back_populates="orders")
    line_items: Mapped[list["OrderLineItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (
        CheckConstraint("total_amount BETWEEN 0.01 AND 99999999.99", name="ck_order_total_range"),
        CheckConstraint(
            "status IN ('PLACED','ACCEPTED','INVOICED','PAID','VERIFIED','SHIPPED','CLOSED','CANCELLED')",
            name="ck_order_status",
        ),
        CheckConstraint("updated_at >= created_at", name="ck_order_updated_after_created"),
        Index("ix_orders_customer_ref", "customer_ref"),
        Index("ix_orders_status", "status"),
    )


class OrderLineItem(Base):
    __tablename__ = "order_line_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_ref: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="line_items")

    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 1000", name="ck_line_item_qty_range"),
        CheckConstraint(
            "unit_price_snapshot BETWEEN 0.01 AND 999999.99", name="ck_line_item_price_range"
        ),
        # Enforces the "no duplicate productRef within same order" rule in the store.
        UniqueConstraint("order_id", "product_ref", name="uq_line_item_order_product"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_ref: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    billing_name: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_address: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    due_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ISSUED")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (
        CheckConstraint("due_date >= issue_date", name="ck_invoice_due_after_issue"),
        CheckConstraint(
            "status IN ('ISSUED','PAID','OVERDUE','CANCELLED')", name="ck_invoice_status"
        ),
        # One live invoice per order.
        UniqueConstraint("order_ref", name="uq_invoice_order_ref"),
        Index("ix_invoices_status", "status"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_ref: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (
        CheckConstraint("amount BETWEEN 0.01 AND 99999999.99", name="ck_payment_amount_range"),
        CheckConstraint("status IN ('PENDING','VERIFIED','REJECTED')", name="ck_payment_status"),
        CheckConstraint(
            "method IN ('CREDIT_CARD','BANK_TRANSFER','E_WALLET')", name="ck_payment_method"
        ),
        Index("ix_payments_order_ref", "order_ref"),
    )
