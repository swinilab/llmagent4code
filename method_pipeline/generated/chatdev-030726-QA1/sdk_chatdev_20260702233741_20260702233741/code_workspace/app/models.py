from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship

# Import shared Base from database module
from .database import Base

class Role(PyEnum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ACCOUNTANT = "accountant"
class OrderStatus(PyEnum):
    CREATED = "created"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class PaymentStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class InvoiceStatus(PyEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(50), nullable=False)
    banking_details = Column(Text, nullable=True)
    role = Column(Enum(Role), default=Role.CUSTOMER, nullable=False)
    # order_history relationship defined via Order.customer_id
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    base_price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    # For simplicity, no stock management

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    customer = relationship("Customer", back_populates="orders")
    line_items = relationship("OrderLineItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", uselist=False)
    payment = relationship("Payment", back_populates="order", uselist=False)

class OrderLineItem(Base):
    __tablename__ = "order_line_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="line_items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    amount = Column(Numeric(12, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    method = Column(String(50), nullable=False)

    order = relationship("Order", back_populates="payment")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    billing_info = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)

    order = relationship("Order", back_populates="invoice")
