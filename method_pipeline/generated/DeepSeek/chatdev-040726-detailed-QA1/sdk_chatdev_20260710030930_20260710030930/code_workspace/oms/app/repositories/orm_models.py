"""SQLAlchemy ORM models for the OMS database schema.

These are the persistence models, separate from the domain Pydantic models.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric as SaDecimal,
    String,
    Text,
    Enum as SaEnum,
    UUID as SaUUID,
)
from sqlalchemy.orm import relationship

from app.domain.enums import (
    Currency,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from app.infrastructure.database import Base


class CustomerModel(Base):
    __tablename__ = "customers"

    id = Column(SaUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(50), nullable=False)
    banking_details = Column(Text, nullable=False)
    order_history = Column(Text, default="[]")  # JSON array of order UUIDs
    role = Column(SaEnum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    orders = relationship("OrderModel", back_populates="customer")


class ProductModel(Base):
    __tablename__ = "products"

    id = Column(SaUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    base_price = Column(SaDecimal(12, 2), nullable=False)
    currency = Column(SaEnum(Currency), default=Currency.USD, nullable=False)
    stock_available = Column(Integer, default=0, nullable=False)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(SaUUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(SaUUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    line_items = Column(Text, default="[]")  # JSON array of line items
    subtotal = Column(SaDecimal(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = Column(SaDecimal(12, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(SaDecimal(12, 2), default=Decimal("0.00"), nullable=False)
    status = Column(SaEnum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    invoice_ref = Column(SaUUID(as_uuid=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)  # Optimistic lock
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    invoiced_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    customer = relationship("CustomerModel", back_populates="orders")
    payments = relationship("PaymentModel", back_populates="order")
    invoices = relationship("InvoiceModel", back_populates="order")


class PaymentModel(Base):
    __tablename__ = "payments"

    id = Column(SaUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id = Column(SaUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    amount = Column(SaDecimal(12, 2), nullable=False)
    currency = Column(SaEnum(Currency), default=Currency.USD, nullable=False)
    status = Column(SaEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    method = Column(SaEnum(PaymentMethod), nullable=False)
    idempotency_key = Column(String(255), unique=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    order = relationship("OrderModel", back_populates="payments")


class InvoiceModel(Base):
    __tablename__ = "invoices"

    id = Column(SaUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id = Column(SaUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_address = Column(Text, nullable=False)
    billing_info = Column(Text, nullable=False)
    subtotal = Column(SaDecimal(12, 2), nullable=False)
    tax_amount = Column(SaDecimal(12, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(SaDecimal(12, 2), nullable=False)
    status = Column(SaEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    issue_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    order = relationship("OrderModel", back_populates="invoices")
