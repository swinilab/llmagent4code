import enum
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum, Boolean, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class CustomerRole(str, enum.Enum):
    customer = "customer"
    order_staff = "order_staff"
    accountant = "accountant"

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(50))
    banking_details = Column(Text)
    role = Column(Enum(CustomerRole), default=CustomerRole.customer)
    order_history = Column(Text)  # simplified as JSON string or relation; we keep simple
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    order_items = relationship("OrderItem", back_populates="product")

class OrderStatus(str, enum.Enum):
    draft = "draft"
    pending_acceptance = "pending_acceptance"
    accepted = "accepted"
    invoiced = "invoiced"
    paid = "paid"
    shipped = "shipped"
    closed = "closed"
    cancelled = "cancelled"

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.draft)
    total_amount = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", uselist=False, back_populates="order")
    payment = relationship("Payment", uselist=False, back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
    )

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"

class PaymentMethod(str, enum.Enum):
    credit_card = "credit_card"
    bank_transfer = "bank_transfer"
    paypal = "paypal"
    cash = "cash"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    order = relationship("Order", back_populates="payment")

class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    issued = "issued"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    billing_info = Column(Text)
    amount = Column(Numeric(10, 2), nullable=False)
    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True))
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft)
    order = relationship("Order", back_populates="invoice")