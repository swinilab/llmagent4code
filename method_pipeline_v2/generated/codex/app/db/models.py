from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import InvoiceStatus, OrderStatus, PaymentMethod, PaymentStatus, Role


def utc_now() -> datetime:
    return datetime.now(UTC)


class VersionedMixin:
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    internal_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class CustomerModel(VersionedMixin, Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    account_number: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, native_enum=False, validate_strings=True, name="role_enum"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("length(name) BETWEEN 2 AND 100", name="customer_name_length"),
        CheckConstraint("length(address) BETWEEN 5 AND 255", name="customer_address_length"),
        CheckConstraint("length(account_number) BETWEEN 6 AND 20", name="account_number_length"),
        CheckConstraint("length(bank_name) BETWEEN 2 AND 100", name="bank_name_length"),
        CheckConstraint(
            "role IN ('CUSTOMER', 'ORDER_STAFF', 'ACCOUNTANT')", name="customer_role_allowed"
        ),
    )


class ProductModel(VersionedMixin, Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)

    __table_args__ = (
        CheckConstraint("length(description) BETWEEN 3 AND 500", name="product_description_length"),
        CheckConstraint("price_amount >= 0.01 AND price_amount <= 999999.99", name="product_price_range"),
        CheckConstraint("price_currency IN ('USD', 'VND', 'EUR')", name="product_currency_allowed"),
    )


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, native_enum=False, validate_strings=True, name="order_status_enum"),
        nullable=False,
        default=OrderStatus.PLACED,
        server_default=OrderStatus.PLACED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    invoice_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL", use_alter=True, name="fk_orders_invoice_id_invoices"),
        nullable=True,
        unique=True,
    )
    items: Mapped[list[OrderItemModel]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("total_amount >= 0.01 AND total_amount <= 99999999.99", name="order_total_range"),
        CheckConstraint("length(currency) = 3", name="order_currency_length"),
        CheckConstraint("updated_at >= created_at", name="order_timestamp_order"),
        CheckConstraint(
            "status IN ('PLACED', 'ACCEPTED', 'INVOICED', 'PAID', 'VERIFIED', 'SHIPPED', 'CLOSED', 'CANCELLED')",
            name="order_status_allowed",
        ),
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    order: Mapped[OrderModel] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        CheckConstraint("quantity >= 1 AND quantity <= 1000", name="order_item_quantity_range"),
        CheckConstraint(
            "unit_price_snapshot >= 0.01 AND unit_price_snapshot <= 999999.99",
            name="order_item_price_range",
        ),
    )


class InvoiceModel(VersionedMixin, Base):
    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    billing_name: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_address: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, native_enum=False, validate_strings=True, name="invoice_status_enum"),
        nullable=False,
        default=InvoiceStatus.ISSUED,
        server_default=InvoiceStatus.ISSUED.value,
    )

    __table_args__ = (
        CheckConstraint("total_amount >= 0.01 AND total_amount <= 99999999.99", name="invoice_total_range"),
        CheckConstraint("due_date >= issue_date", name="invoice_due_after_issue"),
        CheckConstraint("length(billing_name) BETWEEN 2 AND 100", name="invoice_billing_name_length"),
        CheckConstraint(
            "length(billing_address) BETWEEN 5 AND 255", name="invoice_billing_address_length"
        ),
        CheckConstraint(
            "status IN ('ISSUED', 'PAID', 'OVERDUE', 'CANCELLED')", name="invoice_status_allowed"
        ),
    )


class PaymentModel(VersionedMixin, Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False, validate_strings=True, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
    )
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, native_enum=False, validate_strings=True, name="payment_method_enum"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("amount >= 0.01 AND amount <= 99999999.99", name="payment_amount_range"),
        CheckConstraint(
            "status IN ('PENDING', 'VERIFIED', 'REJECTED')", name="payment_status_allowed"
        ),
        CheckConstraint(
            "method IN ('CREDIT_CARD', 'BANK_TRANSFER', 'E_WALLET')", name="payment_method_allowed"
        ),
    )


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_outbox_unpublished_created", "published_at", "created_at"),
        CheckConstraint("attempts >= 0", name="outbox_attempts_nonnegative"),
    )
