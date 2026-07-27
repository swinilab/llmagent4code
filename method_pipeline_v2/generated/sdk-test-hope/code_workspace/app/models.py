from sqlalchemy import Column, String, DateTime, Enum, Integer, Numeric, ForeignKey, JSON, Table, Boolean
from sqlalchemy.orm import relationship, declarative_base
import enum
import datetime

Base = declarative_base()

class RoleEnum(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"

class OrderStatusEnum(str, enum.Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class PaymentStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class PaymentMethodEnum(str, enum.Enum):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"

class InvoiceStatusEnum(str, enum.Enum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    banking_details = Column(JSON, nullable=False)  # {accountNumber, bankName}
    role = Column(Enum(RoleEnum), nullable=False)
    # orderHistory is derived, not stored directly
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True)
    description = Column(String(500), nullable=False)
    price_amount = Column(Numeric(10, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)
    # No relationships needed

class Order(Base):
    __tablename__ = "orders"
    id = Column(String(36), primary_key=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PLACED)
    total_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    customer = relationship("Customer", back_populates="orders")
    line_items = relationship("LineItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", uselist=False)

class LineItem(Base):
    __tablename__ = "line_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_snapshot = Column(Numeric(10, 2), nullable=False)
    order = relationship("Order", back_populates="line_items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(Enum(PaymentStatusEnum), nullable=False, default=PaymentStatusEnum.PENDING)
    method = Column(Enum(PaymentMethodEnum), nullable=False)
    order = relationship("Order")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    billing_name = Column(String(100), nullable=False)
    billing_address = Column(String(255), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(InvoiceStatusEnum), nullable=False, default=InvoiceStatusEnum.ISSUED)
    order = relationship("Order", back_populates="invoice")
