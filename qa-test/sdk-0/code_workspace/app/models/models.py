"""
SQLAlchemy models for OMS entities.
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, Numeric, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Helper for UUID strings
def generate_uuid() -> str:
    return str(uuid.uuid4())

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    banking_account_number = Column(String(20), nullable=False)
    banking_bank_name = Column(String(100), nullable=False)
    role = Column(Enum("CUSTOMER", "ORDER_STAFF", "ACCOUNTANT", name="role_enum"), nullable=False)
    # orderHistory is derived, not stored

class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    description = Column(String(500), nullable=False)
    price_amount = Column(Numeric(12, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(
        "PLACED", "ACCEPTED", "INVOICED", "PAID", "VERIFIED", "SHIPPED", "CLOSED", "CANCELLED",
        name="order_status_enum"), nullable=False, default="PLACED")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    # relationships
    customer = relationship("Customer", backref="orders")
    line_items = relationship("LineItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", backref="order", uselist=False)

class LineItem(Base):
    __tablename__ = "line_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_snapshot = Column(Numeric(12, 2), nullable=False)
    order = relationship("Order", back_populates="line_items")
    product = relationship("Product")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    billing_name = Column(String(100), nullable=False)
    billing_address = Column(String(255), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum("ISSUED", "PAID", "OVERDUE", "CANCELLED", name="invoice_status_enum"), nullable=False, default="ISSUED")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status = Column(Enum("PENDING", "VERIFIED", "REJECTED", name="payment_status_enum"), nullable=False, default="PENDING")
    method = Column(Enum("CREDIT_CARD", "BANK_TRANSFER", "E_WALLET", name="payment_method_enum"), nullable=False)
    order = relationship("Order", backref="payments")
