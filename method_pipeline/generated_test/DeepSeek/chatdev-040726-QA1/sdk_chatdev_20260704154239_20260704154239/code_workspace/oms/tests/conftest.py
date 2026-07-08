"""
Pytest configuration for OMS tests.

Provides a shared in-memory SQLite database fixture used by all test modules.
"""
import sys
import os

# Ensure the oms directory is on the path so 'app' module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.order import OrderCreate, OrderItemCreate, OrderStatusUpdate
from app.schemas.payment import PaymentCreate
from app.schemas.invoice import InvoiceCreate, InvoiceStatusUpdate
from app.services.customer_service import CustomerService
from app.services.product_service import ProductService
from app.services.order_service import OrderService, OrderStateError
from app.services.payment_service import PaymentService, PaymentStateError
from app.services.invoice_service import InvoiceService, InvoiceStateError
from app.services.workflow_service import WorkflowService, WorkflowError


@pytest.fixture(scope="function")
def db() -> Session:
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def customer_data() -> CustomerCreate:
    return CustomerCreate(
        name="Test User",
        address="123 Test St",
        phone="+1-555-0000",
        banking_details="Test Bank, acct: 99999",
        role="customer",
    )


@pytest.fixture
def product_data() -> ProductCreate:
    return ProductCreate(
        name="Test Product",
        description="A test product",
        base_price=19.99,
        currency="USD",
    )


@pytest.fixture
def sample_customer(db: Session, customer_data: CustomerCreate) -> Customer:
    return CustomerService.create(db, customer_data)


@pytest.fixture
def sample_product(db: Session, product_data: ProductCreate) -> Product:
    return ProductService.create(db, product_data)


@pytest.fixture
def sample_order(db: Session, sample_customer: Customer, sample_product: Product) -> Order:
    data = OrderCreate(
        customer_id=sample_customer.id,
        line_items=[
            OrderItemCreate(
                product_id=sample_product.id,
                quantity=2,
                unit_price=19.99,
                currency="USD",
            )
        ],
    )
    return OrderService.create(db, data)
