"""
Database infrastructure for OMS using SQLAlchemy with async support
Implements NFR 2.4 Transactions via ACID-compliant database operations
"""
import uuid
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Type, TypeVar, Generic, List, Any, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import Column, String, Text, DateTime, Numeric, Enum, ForeignKey, Integer, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
import phonenumbers

from oms.config.app_config import AppConfig

config = AppConfig()

# Custom JSON encoder for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

Base = declarative_base()

# ============== SQLAlchemy Models ==============

class CustomerModel(Base):
    """Customer database model"""
    __tablename__ = 'customers'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    account_number = Column(String(20), nullable=False)
    bank_name = Column(String(100), nullable=False)
    role = Column(Enum('CUSTOMER', 'ORDER_STAFF', 'ACCOUNTANT', name='customer_role'), nullable=False)
    order_history = Column(Text, default='[]')  # JSON array of order IDs
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    orders = relationship("OrderModel", back_populates="customer")

class ProductModel(Base):
    """Product database model"""
    __tablename__ = 'products'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    description = Column(String(500), nullable=False)
    price_amount = Column(Numeric(10, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    order_items = relationship("LineItemModel", back_populates="product")

class OrderModel(Base):
    """Order database model"""
    __tablename__ = 'orders'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_ref = Column(String(36), ForeignKey('customers.id'), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(
        'PLACED', 'ACCEPTED', 'INVOICED', 'PAID', 'VERIFIED', 'SHIPPED', 'CLOSED', 'CANCELLED',
        name='order_status'
    ), nullable=False, default='PLACED')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    invoice_ref = Column(String(36), ForeignKey('invoices.id'), nullable=True)
    
    customer = relationship("CustomerModel", back_populates="orders")
    line_items = relationship("LineItemModel", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("PaymentModel", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("InvoiceModel", back_populates="order")

class LineItemModel(Base):
    """Order line item database model"""
    __tablename__ = 'line_items'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=False)
    product_ref = Column(String(36), ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_snapshot = Column(Numeric(10, 2), nullable=False)
    
    order = relationship("OrderModel", back_populates="line_items")
    product = relationship("ProductModel", back_populates="order_items")

class PaymentModel(Base):
    """Payment database model"""
    __tablename__ = 'payments'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_ref = Column(String(36), ForeignKey('orders.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(Enum('PENDING', 'VERIFIED', 'REJECTED', name='payment_status'), nullable=False, default='PENDING')
    method = Column(Enum('CREDIT_CARD', 'BANK_TRANSFER', 'E_WALLET', name='payment_method'), nullable=False)
    
    order = relationship("OrderModel", back_populates="payments")

class InvoiceModel(Base):
    """Invoice database model"""
    __tablename__ = 'invoices'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_ref = Column(String(36), ForeignKey('orders.id'), nullable=False)
    billing_name = Column(String(100), nullable=False)
    billing_address = Column(String(255), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    issue_date = Column(String(10), nullable=False)  # dd/MM/yyyy
    due_date = Column(String(10), nullable=False)  # dd/MM/yyyy
    status = Column(Enum('ISSUED', 'PAID', 'OVERDUE', 'CANCELLED', name='invoice_status'), nullable=False, default='ISSUED')
    
    order = relationship("OrderModel", back_populates="invoice")

# ============== Database Engine Setup ==============

_engine = None
_async_session_maker = None

async def init_db():
    """Initialize database engine and create tables"""
    global _engine, _async_session_maker
    
    _engine = create_async_engine(config.database_url, echo=False, future=True)
    _async_session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    async with _async_session_maker() as session:
        yield session


@asynccontextmanager
async def transaction_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database transactions.
    Implements NFR 2.4: Ensures ACID properties for database operations.
    Automatically commits on success, rolls back on exception.
    """
    async with _async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ============== Repository Base ==============

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Base repository with CRUD operations and transaction support"""
    
    def __init__(self, model_class: Type[T], session: AsyncSession):
        self.model_class = model_class
        self.session = session
        self.model_class = model_class
        self.session = session
    
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID"""
        result = await self.session.execute(select(self.model_class).where(self.model_class.id == id))
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[T]:
        """Get all entities"""
        result = await self.session.execute(select(self.model_class))
        return list(result.scalars().all())
    
    async def create(self, entity: T) -> T:
        """Create entity with transaction"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def update(self, entity: T) -> T:
        """Update entity with transaction"""
        await self.session.merge(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        entity = await self.get_by_id(id)
        if entity:
            await self.session.delete(entity)
            await self.session.flush()
            return True
        return False
    
    async def commit(self):
        """Commit transaction"""
        await self.session.commit()
    
    async def rollback(self):
        """Rollback transaction"""
        await self.session.rollback()

# ============== Specific Repositories ==============

class CustomerRepository(BaseRepository[CustomerModel]):
    """Customer repository with specialized queries"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(CustomerModel, session)
    
    async def add_to_order_history(self, customer_id: str, order_id: str) -> bool:
        """Add order to customer's order history"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return False
        
        history = json.loads(customer.order_history or '[]')
        if order_id not in history:
            history.append(order_id)
            customer.order_history = json.dumps(history)
            await self.session.flush()
        return True

class ProductRepository(BaseRepository[ProductModel]):
    """Product repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ProductModel, session)

class OrderRepository(BaseRepository[OrderModel]):
    """Order repository with specialized queries"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(OrderModel, session)
    
    async def get_by_customer(self, customer_id: str) -> List[OrderModel]:
        """Get orders by customer ID"""
        result = await self.session.execute(
            select(OrderModel).where(OrderModel.customer_ref == customer_id)
        )
        return list(result.scalars().all())
    
    async def get_by_status(self, status: str) -> List[OrderModel]:
        """Get orders by status"""
        result = await self.session.execute(
            select(OrderModel).where(OrderModel.status == status)
        )
        return list(result.scalars().all())

class PaymentRepository(BaseRepository[PaymentModel]):
    """Payment repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(PaymentModel, session)
    
    async def get_by_order(self, order_id: str) -> List[PaymentModel]:
        """Get payments by order ID"""
        result = await self.session.execute(
            select(PaymentModel).where(PaymentModel.order_ref == order_id)
        )
        return list(result.scalars().all())

class InvoiceRepository(BaseRepository[InvoiceModel]):
    """Invoice repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(InvoiceModel, session)
    
    async def get_by_order(self, order_id: str) -> Optional[InvoiceModel]:
        """Get invoice by order ID"""
        result = await self.session.execute(
            select(InvoiceModel).where(InvoiceModel.order_ref == order_id)
        )
        return result.scalar_one_or_none()
__all__ = [
    'Base', 'CustomerModel', 'ProductModel', 'OrderModel', 'LineItemModel',
    'PaymentModel', 'InvoiceModel',
    'init_db', 'get_async_session', 'transaction_session',
    'BaseRepository', 'CustomerRepository', 'ProductRepository',
    'OrderRepository', 'PaymentRepository', 'InvoiceRepository'
]
