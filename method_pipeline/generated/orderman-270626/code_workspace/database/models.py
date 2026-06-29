"""
SQLAlchemy ORM models for the Order Management System.
These models map to the database tables and are compatible with shared domain models.
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import enum

from database.config import DATABASE_URL


class RegistryBase:
    """Base class for all ORM models."""
    pass


Base = declarative_base(cls=RegistryBase)


# ============================================================================
# Enum Classes for SQLAlchemy
# ============================================================================

class UserRoleEnum(enum.Enum):
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"


class OrderStatusEnum(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatusEnum(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatusEnum(enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# ============================================================================
# Customer Model
# ============================================================================

class CustomerModel(Base):
    """SQLAlchemy model for Customer entity."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    banking_details = Column(Text, nullable=True)
    role = Column(Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.CUSTOMER)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("OrderModel", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("InvoiceModel", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("PaymentModel", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}', email='{self.email}')>"


# ============================================================================
# Product Model
# ============================================================================

class ProductModel(Base):
    """SQLAlchemy model for Product entity."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    sku = Column(String(50), nullable=False, unique=True)
    stock_quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order_items = relationship("OrderItemModel", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}')>"


# ============================================================================
# Order Model
# ============================================================================

class OrderModel(Base):
    """SQLAlchemy model for Order entity."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING)
    total_amount = Column(Float, nullable=False, default=0.0)
    shipping_address = Column(String(500), nullable=False)
    notes = Column(Text, nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    # Relationships
    customer = relationship("CustomerModel", back_populates="orders")
    items = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("InvoiceModel", back_populates="order", foreign_keys="InvoiceModel.order_id", uselist=False)
# Order Item Model
# ============================================================================

class OrderItemModel(Base):
    """SQLAlchemy model for Order Item entity."""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relationships
    order = relationship("OrderModel", back_populates="items")
    product = relationship("ProductModel", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id})>"


# ============================================================================
# Invoice Model
# ============================================================================

class InvoiceModel(Base):
    """SQLAlchemy model for Invoice entity."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String(50), nullable=False, unique=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(InvoiceStatusEnum), nullable=False, default=InvoiceStatusEnum.DRAFT)
    billing_address = Column(String(500), nullable=False)
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    order = relationship("OrderModel", back_populates="invoice", foreign_keys=[order_id])
    customer = relationship("CustomerModel", back_populates="invoices")
    payments = relationship("PaymentModel", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', amount={self.amount})>"



# ============================================================================
# Payment Model
# ============================================================================

class PaymentModel(Base):
    """SQLAlchemy model for Payment entity."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatusEnum), nullable=False, default=PaymentStatusEnum.PENDING)
    payment_method = Column(String(100), nullable=False)
    transaction_id = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    invoice = relationship("InvoiceModel", back_populates="payments")
    customer = relationship("CustomerModel", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount})>"



# ============================================================================
# ============================================================================
# Database Engine and Session Management (Singleton Pattern)
# ============================================================================

# Module-level singleton engine instance
_engine = None
_session_factory = None


def get_engine():
    """Get the singleton database engine instance."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
        )
    return _engine


def get_session_factory():
    """Get the singleton session factory instance."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session():
    """Get a database session for dependency injection."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def init_db():
    """Initialize the database by creating all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def dispose_engine():
    """Dispose of the database engine (call on shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
