"""SQLAlchemy models reflecting the domain entities and constraints.

All constraints from the Field Constraint Table are enforced here where possible.
"""

import datetime
import uuid
from typing import List

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    JSON,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()

# Enums
class OrderStatus(str, Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class PaymentMethod(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"

# Helper for UUID generation
def generate_uuid() -> str:
    return str(uuid.uuid4())

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    banking_details: Mapped[dict] = mapped_column(JSON, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # orderHistory is derived – not stored here

class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    customer_ref: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    line_items: Mapped[List[dict]] = mapped_column(JSON, nullable=False)  # stored as list of dicts
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.PLACED)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    invoice_ref: Mapped[str | None] = mapped_column(String(36), ForeignKey("invoices.id"), nullable=True)

class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    order_ref: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), nullable=False)
    billing_info: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    issue_date: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ISSUED")

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    order_ref: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)

# Async engine and session factory
engine = create_async_engine("sqlite+aiosqlite:///./data/oms.db", echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

# Provide a convenient async context manager for each model
for model in (Customer, Product, Order, Invoice, Payment):
    async def async_session(cls=model):
        return AsyncSessionLocal()
    model.async_session = classmethod(async_session)
