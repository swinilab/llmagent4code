"""
SQLAlchemy ORM models for database persistence
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
import uuid
from enum import Enum as PyEnum

Base = declarative_base()


# Enums
class CustomerRole(str, PyEnum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


class OrderStatus(str, PyEnum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, PyEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class PaymentMethod(str, PyEnum):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"


class InvoiceStatus(str, PyEnum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class CustomerModel(Base):
    """Customer database model"""
    __tablename__ = "customers"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    account_number = Column(String(20), nullable=False)
    bank_name = Column(String(100), nullable=False)
    role = Column(Enum(CustomerRole), nullable=False, default=CustomerRole.CUSTOMER)
    order_history = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    orders = relationship("OrderModel", back_populates="customer")


class ProductModel(Base):
    """Product database model"""
    __tablename__ = "products"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text, nullable=False)
    price_amount = Column(Numeric(10, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OrderModel(Base):
    """Order database model"""
    __tablename__ = "orders"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_ref = Column(PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    line_items = Column(JSONB, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PLACED)
    invoice_ref = Column(PG_UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    customer = relationship("CustomerModel", back_populates="orders")
    payments = relationship("PaymentModel", back_populates="order")
    invoice = relationship("InvoiceModel", back_populates="order", uselist=False)


class PaymentModel(Base):
    """Payment database model"""
    __tablename__ = "payments"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_ref = Column(PG_UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    method = Column(Enum(PaymentMethod), nullable=False)
    
    order = relationship("OrderModel", back_populates="payments")


class InvoiceModel(Base):
    """Invoice database model"""
    __tablename__ = "invoices"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_ref = Column(PG_UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    billing_name = Column(String(100), nullable=False)
    billing_address = Column(String(255), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    issue_date = Column(String(10), nullable=False)  # dd/MM/yyyy format
    due_date = Column(String(10), nullable=False)  # dd/MM/yyyy format
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.ISSUED)
    
    order = relationship("OrderModel", back_populates="invoice")
