"""
SQLAlchemy ORM models for the OMS.
Every model includes a `version` column for optimistic locking and
`created_at`/`updated_at` timestamps for auditability.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Text, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from oms.database import Base
from oms.models.enums import (
    OrderStatus, PaymentStatus, PaymentMethod, InvoiceStatus, OutboxStatus, UserRole,
)


def _utcnow():
    return datetime.now(timezone.utc)


def _new_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
class CustomerModel(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(50), nullable=False)
    banking_details = Column(Text, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow,
                       onupdate=_utcnow, nullable=False)

    orders = relationship("OrderModel", back_populates="customer",
                          cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class ProductModel(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    description = Column(Text, nullable=False)
    base_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow,
                       onupdate=_utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    invoice_ref = Column(String(36), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow,
                       onupdate=_utcnow, nullable=False)

    customer = relationship("CustomerModel", back_populates="orders")
    line_items = relationship("OrderLineItemModel", back_populates="order",
                              cascade="all, delete-orphan")
    payments = relationship("PaymentModel", back_populates="order",
                            cascade="all, delete-orphan")
    invoices = relationship("InvoiceModel", back_populates="order",
                            cascade="all, delete-orphan")


class OrderLineItemModel(Base):
    """Individual line item within an order."""
    __tablename__ = "order_line_items"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    order = relationship("OrderModel", back_populates="line_items")
    product = relationship("ProductModel")


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class PaymentModel(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    method = Column(SAEnum(PaymentMethod), nullable=False)
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING,
                    nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow,
                       onupdate=_utcnow, nullable=False)

    order = relationship("OrderModel", back_populates="payments")


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
class InvoiceModel(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    billing_name = Column(String(200), nullable=False)
    billing_address = Column(Text, nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT,
                    nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow,
                       onupdate=_utcnow, nullable=False)

    order = relationship("OrderModel", back_populates="invoices")


# ---------------------------------------------------------------------------
# Outbox – transactional outbox pattern for state preservation (NFR 2.3)
# ---------------------------------------------------------------------------
class OutboxMessage(Base):
    """
    Durable outbox table. Every critical state transition is first persisted
    here (in the same transaction as the domain entity), then a background
    worker processes the message. On restart, unprocessed messages are
    replayed, ensuring no order state is lost (NFR 2.3).
    """
    __tablename__ = "outbox_messages"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    aggregate_type = Column(String(100), nullable=False)   # e.g. "order"
    aggregate_id = Column(String(36), nullable=False)      # e.g. order.id
    event_type = Column(String(100), nullable=False)       # e.g. "order.created"
    payload = Column(Text, nullable=False)                 # JSON-serialised dict
    status = Column(SAEnum(OutboxStatus), default=OutboxStatus.PENDING,
                    nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
