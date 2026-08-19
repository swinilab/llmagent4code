"""
SQLAlchemy ORM models for OMS entities
Implements all field constraints from the Field Constraint Table
"""
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Enum, Numeric, Text, Boolean
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
from enum import Enum as PyEnum
import uuid
import re

Base = declarative_base()


class OrderStatus(str, PyEnum):
    """Order lifecycle status enum"""
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, PyEnum):
    """Payment status enum"""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class InvoiceStatus(str, PyEnum):
    """Invoice status enum"""
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, PyEnum):
    """Payment method enum"""
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"


class CustomerRole(str, PyEnum):
    """Customer role enum"""
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


def generate_uuid() -> str:
    """Generate a UUIDv4 string"""
    return str(uuid.uuid4())


def validate_uuid(value: str) -> bool:
    """Validate UUID format"""
    try:
        uuid.UUID(value, version=4)
        return True
    except (ValueError, AttributeError):
        return False


def validate_phone(value: str) -> bool:
    """Validate phone number: E.164 format, 8-15 digits"""
    pattern = r'^\+?[1-9]\d{7,14}$'
    return bool(re.match(pattern, value))


def validate_name(value: str) -> bool:
    """Validate name: 2-100 chars, letters, spaces, dots, hyphens, apostrophes"""
    if not value or len(value) < 2 or len(value) > 100:
        return False
    pattern = r'^[\p{L} .\'-]+$'
    return bool(re.match(pattern, value, re.UNICODE))


def validate_address(value: str) -> bool:
    """Validate address: 5-255 chars, not blank"""
    if not value or len(value) < 5 or len(value) > 255:
        return False
    return value.strip() != ""


def validate_account_number(value: str) -> bool:
    """Validate account number: 6-20 digits"""
    if not value or len(value) < 6 or len(value) > 20:
        return False
    return value.isdigit()


def validate_bank_name(value: str) -> bool:
    """Validate bank name: 2-100 chars, letters, numbers, spaces, dots, ampersands, hyphens"""
    if not value or len(value) < 2 or len(value) > 100:
        return False
    pattern = r'^[\p{L}0-9 .&-]+$'
    return bool(re.match(pattern, value, re.UNICODE))


def validate_description(value: str) -> bool:
    """Validate product description: 3-500 chars, not blank"""
    if not value or len(value) < 3 or len(value) > 500:
        return False
    return value.strip() != ""


def validate_currency(value: str) -> bool:
    """Validate currency: 3 uppercase letters, ISO 4217"""
    if not value or len(value) != 3:
        return False
    pattern = r'^[A-Z]{3}$'
    return bool(re.match(pattern, value)) and value in ["USD", "VND", "EUR"]


def validate_price_amount(value: str) -> bool:
    """Validate price amount: 0.01 to 999999.99, exactly 2 decimal places"""
    if not value:
        return False
    pattern = r'^\d{1,6}\.\d{2}$'
    if not re.match(pattern, value):
        return False
    try:
        amount = float(value)
        return 0.01 <= amount <= 999999.99
    except ValueError:
        return False


def validate_date_format(value: str) -> bool:
    """Validate date format: dd/MM/yyyy"""
    if not value:
        return False
    pattern = r'^\d{2}/\d{2}/\d{4}$'
    if not re.match(pattern, value):
        return False
    # Check calendar validity
    try:
        day, month, year = map(int, value.split('/'))
        datetime(year=year, month=month, day=day)
        return True
    except ValueError:
        return False


class Customer(Base):
    """Customer entity with all field constraints"""
    __tablename__ = "customers"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    banking_details = Column(JSON, nullable=False)
    role = Column(Enum(CustomerRole), nullable=False, default=CustomerRole.CUSTOMER)
    order_history = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    orders = relationship("Order", back_populates="customer")


class Product(Base):
    """Product entity with all field constraints"""
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    description = Column(String(500), nullable=False)
    price_amount = Column(Numeric(10, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Order(Base):
    """Order entity with all field constraints"""
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_ref = Column(String(36), ForeignKey("customers.id"), nullable=False)
    line_items = Column(JSON, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PLACED)
    invoice_ref = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    customer = relationship("Customer", back_populates="orders")
    invoice = relationship("Invoice", back_populates="order", uselist=False)
    payments = relationship("Payment", back_populates="order")


class Payment(Base):
    """Payment entity with all field constraints"""
    __tablename__ = "payments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_ref = Column(String(36), ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    method = Column(Enum(PaymentMethod), nullable=False)
    
    order = relationship("Order", back_populates="payments")


class Invoice(Base):
    """Invoice entity with all field constraints"""
    __tablename__ = "invoices"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_ref = Column(String(36), ForeignKey("orders.id"), nullable=False)
    billing_info = Column(JSON, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    issue_date = Column(String(10), nullable=False)
    due_date = Column(String(10), nullable=False)
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.ISSUED)
    
    order = relationship("Order", back_populates="invoice")
