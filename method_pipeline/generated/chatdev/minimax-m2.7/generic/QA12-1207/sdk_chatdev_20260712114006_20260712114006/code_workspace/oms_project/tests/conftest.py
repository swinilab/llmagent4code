"""
OMS Test Fixtures - Shared test utilities and fixtures.
"""
import pytest
import os
import tempfile
from decimal import Decimal

from app.core.config import AppConfig, configure_app, ServiceRegistry
from app.core.events import get_event_bus
from app.domain.entities.models import (
    Customer, Product, Order, Payment, Invoice,
    Address, Money, Currency, UserRole, LineItem, OrderStatus
)
from app.adapters.persistence import (
    DatabaseManager, InMemoryCustomerRepository, InMemoryOrderRepository,
    InMemoryProductRepository, InMemoryPaymentRepository, InMemoryInvoiceRepository
)


@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture(scope="function")
def db_manager(temp_db):
    """Create a database manager with initialized schema."""
    manager = DatabaseManager(temp_db)
    manager.init_schema()
    return manager


@pytest.fixture(scope="function")
def customer_repo(db_manager):
    """Create a customer repository."""
    return InMemoryCustomerRepository(db_manager)


@pytest.fixture(scope="function")
def product_repo(db_manager):
    """Create a product repository."""
    return InMemoryProductRepository(db_manager)


@pytest.fixture(scope="function")
def order_repo(db_manager):
    """Create an order repository."""
    return InMemoryOrderRepository(db_manager)


@pytest.fixture(scope="function")
def payment_repo(db_manager):
    """Create a payment repository."""
    return InMemoryPaymentRepository(db_manager)


@pytest.fixture(scope="function")
def invoice_repo(db_manager):
    """Create an invoice repository."""
    return InMemoryInvoiceRepository(db_manager)


@pytest.fixture(scope="function")
def sample_address():
    """Create a sample address."""
    return Address(
        street="123 Test St",
        city="Test City",
        state="TS",
        postal_code="12345",
        country="USA"
    )


@pytest.fixture(scope="function")
def sample_customer(sample_address):
    """Create a sample customer."""
    return Customer(
        id="cust-001",
        name="Test Customer",
        email="test@example.com",
        phone="+1234567890",
        address=sample_address,
        role=UserRole.CUSTOMER
    )


@pytest.fixture(scope="function")
def sample_product():
    """Create a sample product."""
    return Product(
        id="prod-001",
        sku="LAPTOP-001",
        name="Test Laptop",
        description="A test laptop",
        price=Money(amount=Decimal("999.99"), currency=Currency.USD),
        stock_quantity=10,
        category="Electronics"
    )


@pytest.fixture(scope="function")
def sample_order(sample_customer, sample_product):
    """Create a sample order."""
    line_item = LineItem(
        product_id=sample_product.id,
        product_name=sample_product.name,
        sku=sample_product.sku,
        quantity=1,
        unit_price=sample_product.price,
        subtotal=sample_product.price
    )
    return Order(
        id="ord-001",
        customer_id=sample_customer.id,
        line_items=[line_item],
        status=OrderStatus.PENDING,
        subtotal=sample_product.price,
        tax_total=Money(amount=Decimal("0"), currency=Currency.USD),
        discount_total=Money(amount=Decimal("0"), currency=Currency.USD),
        total=sample_product.price,
        currency=Currency.USD
    )


@pytest.fixture(scope="function")
def configured_app(db_manager):
    """Configure app with test database."""
    config = AppConfig(
        database__path=":memory:",
        debug=True
    )
    registry = ServiceRegistry()
    registry._db_manager = db_manager
    registry._setup_repositories()
    yield registry
    registry.reset()
