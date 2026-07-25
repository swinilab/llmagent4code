"""
SQLAlchemy ORM table definitions for OMS entities
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Numeric, Boolean, Table, MetaData
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.sqlite import JSON
import uuid
from datetime import datetime

Base = declarative_base()
metadata = MetaData()


def generate_uuid():
    """Generate UUID string"""
    return str(uuid.uuid4())


class CustomerTable(Base):
    """Customer table"""
    __tablename__ = "customers"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    banking_account_number = Column(String(20), nullable=False)
    banking_bank_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="CUSTOMER")
    order_history = Column(JSON, default=lambda: [], nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductTable(Base):
    """Product table"""
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    description = Column(String(500), nullable=False)
    price_amount = Column(Numeric(10, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderTable(Base):
    """Order table"""
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_ref = Column(String(36), ForeignKey("customers.id"), nullable=False)
    line_items = Column(JSON, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="PLACED")
    invoice_ref = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentTable(Base):
    """Payment table"""
    __tablename__ = "payments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_ref = Column(String(36), ForeignKey("orders.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="PENDING")
    method = Column(String(20), nullable=False)


class InvoiceTable(Base):
    """Invoice table"""
    __tablename__ = "invoices"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_ref = Column(String(36), ForeignKey("orders.id"), nullable=False)
    billing_name = Column(String(100), nullable=False)
    billing_address = Column(String(255), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    issue_date = Column(String(10), nullable=False)
    due_date = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="ISSUED")
    created_at = Column(DateTime, default=datetime.utcnow)


async def create_tables(engine):
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
