"""
SQLAlchemy ORM entities for the Order Management System.

Defines the database schema for all domain entities with proper relationships,
indexes, and constraints for production use.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Numeric,
    ForeignKey,
    Enum as SQLEnum,
    Index,
    Boolean,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class OrderStatus(str, Enum):
    """Order lifecycle status enum."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatus(str, Enum):
    """Invoice status enum."""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Customer(Base):
    """
    Customer entity representing a user in the OMS.
    
    Attributes:
        id: Primary key
        name: Customer full name
        email: Customer email address
        phone: Customer phone number
        address: Customer shipping/billing address
        banking_details: Encrypted banking information
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        is_active: Account active status
    """
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    banking_details = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    orders = relationship("Order", back_populates="customer", lazy="select")
    
    __table_args__ = (
        Index("idx_customers_email", "email"),
        Index("idx_customers_name", "name"),
    )
    
    def to_dict(self) -> dict:
        """Convert entity to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "banking_details": self.banking_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }


class Product(Base):
    """
    Product entity representing items available for purchase.
    
    Attributes:
        id: Primary key
        name: Product name
        description: Product description
        base_price: Base price in cents (to avoid floating point issues)
        currency: Currency code (ISO 4217)
        stock_quantity: Available stock
        is_available: Product availability status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    order_line_items = relationship("OrderLineItem", back_populates="product", lazy="select")
    
    __table_args__ = (
        Index("idx_products_name", "name"),
        Index("idx_products_available", "is_available"),
    )
    
    def to_dict(self) -> dict:
        """Convert entity to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "base_price": float(self.base_price),
            "currency": self.currency,
            "stock_quantity": self.stock_quantity,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Order(Base):
    """
    Order entity representing a customer order.
    
    Attributes:
        id: Primary key
        customer_id: Foreign key to Customer
        status: Current order status
        total_amount: Order total amount
        currency: Currency code
        shipping_address: Delivery address
        notes: Order notes
        created_at: Order creation timestamp
        updated_at: Last update timestamp
        shipped_at: Shipping timestamp
        completed_at: Completion timestamp
        invoice_id: Foreign key to Invoice
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    total_amount = Column(Numeric(12, 2), default=0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    shipping_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    shipped_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    
    customer = relationship("Customer", back_populates="orders", lazy="joined")
    line_items = relationship("OrderLineItem", back_populates="order", lazy="select", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", lazy="select", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", lazy="select", uselist=False, foreign_keys=[invoice_id], remote_side="Invoice.order_id")
    
    __table_args__ = (
        Index("idx_orders_customer", "customer_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_created", "created_at"),
        Index("idx_orders_customer_status", "customer_id", "status"),
    )
    
    def to_dict(self) -> dict:
        """Convert entity to dictionary representation."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "status": self.status.value,
            "total_amount": float(self.total_amount),
            "currency": self.currency,
            "shipping_address": self.shipping_address,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "invoice_id": self.invoice_id,
            "line_items": [item.to_dict() for item in self.line_items],
            "customer": self.customer.to_dict() if self.customer else None,
        }


class OrderLineItem(Base):
    """
    Order line item entity representing individual items in an order.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to Order
        product_id: Foreign key to Product
        quantity: Item quantity
        unit_price: Price per unit at time of order
        subtotal: Line item subtotal
        created_at: Creation timestamp
    """
    __tablename__ = "order_line_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    order = relationship("Order", back_populates="line_items", lazy="joined")
    product = relationship("Product", back_populates="order_line_items", lazy="joined")
    
    __table_args__ = (
        Index("idx_line_items_order", "order_id"),
        Index("idx_line_items_product", "product_id"),
    )
    
    def to_dict(self) -> dict:
        """Convert entity to dictionary representation."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "subtotal": float(self.subtotal),
            "product": self.product.to_dict() if self.product else None,
        }


class Payment(Base):
    """
    Payment entity representing a payment transaction.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to Order
        amount: Payment amount
        currency: Currency code
        method: Payment method (card, bank_transfer, etc.)
        status: Payment status
        transaction_id: External payment processor transaction ID
        processed_at: Payment processing timestamp
        created_at: Creation timestamp
    """
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    method = Column(String(50), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    transaction_id = Column(String(255), nullable=True, unique=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    order = relationship("Order", back_populates="payments", lazy="joined")
    
    __table_args__ = (
        Index("idx_payments_order", "order_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_transaction", "transaction_id"),
    )
    
    def to_dict(self) -> dict:
        """Convert entity to dictionary representation."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "amount": float(self.amount),
            "currency": self.currency,
            "method": self.method,
            "status": self.status.value,
            "transaction_id": self.transaction_id,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Invoice(Base):
    """
    Invoice entity representing a billing document.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to Order (one-to-one)
        invoice_number: Unique invoice number
        billing_name: Billing contact name
        billing_address: Billing address
        subtotal: Invoice subtotal
        tax_amount: Tax amount
        total_amount: Invoice total
        issue_date: Invoice issue date
        due_date: Invoice due date
        status: Invoice status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)
    billing_name = Column(String(255), nullable=False)
    billing_address = Column(Text, nullable=True)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    order = relationship("Order", back_populates="invoice", lazy="joined", foreign_keys=[order_id], uselist=False)
    order = relationship("Order", back_populates="invoice", lazy="joined", foreign_keys=[order_id], uselist=False, remote_side="Order.invoice_id")
    __table_args__ = (
        Index("idx_invoices_order", "order_id"),
        Index("idx_invoices_number", "invoice_number"),
        Index("idx_invoices_status", "status"),
        Index("idx_invoices_due_date", "due_date"),
    )
    
    def to_dict(self) -> dict:
        """Convert entity to dictionary representation."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "invoice_number": self.invoice_number,
            "billing_name": self.billing_name,
            "billing_address": self.billing_address,
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "total_amount": float(self.total_amount),
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
