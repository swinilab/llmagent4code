"""SQLAlchemy ORM models for OMS domain.
All models inherit from Base defined in database.py.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base
import enum

class RoleEnum(str, enum.Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ACCOUNTANT = "accountant"

class OrderStatusEnum(str, enum.Enum):
    CREATED = "created"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class InvoiceStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    banking_details = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.CUSTOMER)
    # relationship to orders
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    # relationship to order line items
    line_items = relationship("OrderLineItem", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatusEnum), default=OrderStatusEnum.CREATED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # relationships
    customer = relationship("Customer", back_populates="orders")
    line_items = relationship("OrderLineItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", uselist=False, back_populates="order")
    invoice = relationship("Invoice", uselist=False, back_populates="order")

class OrderLineItem(Base):
    __tablename__ = "order_line_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    # relationships
    order = relationship("Order", back_populates="line_items")
    product = relationship("Product", back_populates="line_items")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    amount = Column(Float, nullable=False)
    method = Column(String, nullable=False)
    status = Column(Enum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING)
    timestamp = Column(DateTime, default=datetime.utcnow)
    # relationship
    order = relationship("Order", back_populates="payment")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    billing_info = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    status = Column(Enum(InvoiceStatusEnum), default=InvoiceStatusEnum.DRAFT)
    # relationship
    order = relationship("Order", back_populates="invoice")
