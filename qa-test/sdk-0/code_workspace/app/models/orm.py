"""SQLAlchemy ORM models"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Numeric, Table, JSON
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table for Order line items (simplified as JSON column)

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    banking_details = Column(JSON, nullable=False)  # {"accountNumber": str, "bankName": str}
    role = Column(Enum("CUSTOMER", "ORDER_STAFF", "ACCOUNTANT", name="role_enum"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    description = Column(String(500), nullable=False)
    price_amount = Column(Numeric(10, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    line_items = Column(JSON, nullable=False)  # list of {productRef, quantity, unitPriceSnapshot}
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum(
        "PLACED", "ACCEPTED", "INVOICED", "PAID", "VERIFIED", "SHIPPED", "CLOSED", "CANCELLED",
        name="order_status_enum"
    ), nullable=False, default="PLACED")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    customer = relationship("Customer")
    invoice = relationship("Invoice", back_populates="order", uselist=False)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    billing_info = Column(JSON, nullable=False)  # {name, address}
    total_amount = Column(Numeric(12, 2), nullable=False)
    issue_date = Column(String(10), nullable=False)  # dd/MM/yyyy
    due_date = Column(String(10), nullable=False)
    status = Column(Enum("ISSUED", "PAID", "OVERDUE", "CANCELLED", name="invoice_status_enum"), nullable=False, default="ISSUED")
    created_at = Column(DateTime, default=datetime.utcnow)
    order = relationship("Order", back_populates="invoice")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum("PENDING", "VERIFIED", "REJECTED", name="payment_status_enum"), nullable=False, default="PENDING")
    method = Column(Enum("CREDIT_CARD", "BANK_TRANSFER", "E_WALLET", name="payment_method_enum"), nullable=False)
    order = relationship("Order")
