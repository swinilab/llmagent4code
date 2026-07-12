"""
SQLAlchemy ORM models for OMS persistence.
These are mapped to the domain models but handle database-specific concerns.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, ForeignKey,
    Text, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
from ..infrastructure.database import Base
import enum


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class UserRoleEnum(str, enum.Enum):
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"


class CustomerModel(Base):
    """Customer database model."""
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    address_json = Column(JSON)
    banking_details_json = Column(JSON)
    role = Column(String(20), default=UserRoleEnum.CUSTOMER.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("OrderModel", back_populates="customer", lazy="dynamic")
    payments = relationship("PaymentModel", back_populates="customer", lazy="dynamic")


class ProductModel(Base):
    """Product database model."""
    __tablename__ = "products"

    id = Column(String(36), primary_key=True)
    sku = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    base_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    line_items = relationship("LineItemModel", back_populates="product", lazy="dynamic")


class OrderModel(Base):
    """Order database model."""
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    status = Column(String(20), default=OrderStatusEnum.PENDING.value)
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    shipping = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    shipping_address_json = Column(JSON)
    billing_address_json = Column(JSON)
    notes = Column(Text, default="")
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    tracking_number = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    customer = relationship("CustomerModel", back_populates="orders")
    invoice = relationship("InvoiceModel", back_populates="order", foreign_keys=[invoice_id])
    payments = relationship("PaymentModel", back_populates="order", lazy="dynamic")
    line_items = relationship("LineItemModel", back_populates="order", lazy="dynamic")


class LineItemModel(Base):
    """Line item embedded in order."""
    __tablename__ = "line_items"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"))
    product_description = Column(String(500))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")

    order = relationship("OrderModel", back_populates="line_items")
    product = relationship("ProductModel", back_populates="line_items")


class InvoiceModel(Base):
    """Invoice database model."""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    billing_address_json = Column(JSON)
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default=InvoiceStatusEnum.DRAFT.value)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    paid_date = Column(DateTime, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("OrderModel", back_populates="invoice", foreign_keys=[OrderModel.invoice_id])
    customer = relationship("CustomerModel")


class PaymentModel(Base):
    """Payment database model."""
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    method = Column(String(50), default="bank_transfer")
    status = Column(String(20), default=PaymentStatusEnum.PENDING.value)
    transaction_ref = Column(String(255))
    idempotency_key = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    order = relationship("OrderModel", back_populates="payments")
    customer = relationship("CustomerModel", back_populates="payments")
    invoice = relationship("InvoiceModel")


class StateSnapshotModel(Base):
    """State snapshot for crash recovery (NFR 2.3)."""
    __tablename__ = "state_snapshots"

    id = Column(String(36), primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    state_json = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_event = Column(String(255))
    is_recovery_point = Column(Boolean, default=False)
