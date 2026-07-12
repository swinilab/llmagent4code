"""
Pytest fixtures — shared test infrastructure.
Provides async DB session, test client, and reusable test data.
"""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Patch settings before importing app
import os
os.environ["OMS_CONFIG"] = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

from server import create_app
from db.connection import get_session
from models.orm_models import Base, Customer, Order, LineItem, Product, Invoice, Payment, Sequence
from schemas.domain import CustomerCreate, ProductCreate, LineItemCreate


# ── Async session fixture ────────────────────────────────────────────────────

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@10.60.190.97:5432/oms_db"

_test_engine = None
_test_session_factory = None


def get_test_engine():
    global _test_engine
    if _test_engine is None:
        _test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    return _test_engine


def get_test_session_factory():
    global _test_session_factory
    if _test_session_factory is None:
        _test_session_factory = sessionmaker(
            get_test_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _test_session_factory


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_test_session_factory()
    session = factory()
    try:
        yield session
        await session.rollback()
    finally:
        await session.close()


# ── FastAPI test client ──────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _get_test_session():
        factory = get_test_session_factory()
        session = factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    app.dependency_overrides[get_session] = _get_test_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Reusable test data factories ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def sample_customer(db_session: AsyncSession) -> Customer:
    customer = Customer(
        id=uuid.uuid4(),
        code="CUST-00001",
        name="Test Customer",
        email="test@example.com",
        role="customer",
        address_line1="123 Main St",
        city="New York",
        state="NY",
        postal_code="10001",
        country="US",
    )
    db_session.add(customer)
    await db_session.flush()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture
async def sample_product(db_session: AsyncSession) -> Product:
    product = Product(
        id=uuid.uuid4(),
        sku="TEST-SKU-001",
        name="Test Product",
        description="A product for testing",
        base_price=Decimal("49.99"),
        currency="USD",
        stock_qty=100,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def sample_invoice_data(db_session: AsyncSession, sample_customer: Customer) -> tuple[Customer, uuid.UUID]:
    """Create a customer + product + order chain, return (customer, order_id)."""
    # Create product
    product = Product(
        id=uuid.uuid4(),
        sku="INV-TEST-SKU",
        name="Invoice Test Product",
        base_price=Decimal("99.99"),
        currency="USD",
        stock_qty=50,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()

    # Create order
    from models.orm_models import Order
    order = Order(
        id=uuid.uuid4(),
        code="ORD-INVTEST-001",
        customer_id=sample_customer.id,
        status="accepted",
        subtotal=Decimal("99.99"),
        tax_amount=Decimal("8.25"),
        total_amount=Decimal("108.24"),
        currency="USD",
    )
    db_session.add(order)
    await db_session.flush()

    # Line item
    li = LineItem(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("99.99"),
        tax_rate=Decimal("0.0825"),
        line_total=Decimal("108.24"),
    )
    db_session.add(li)
    await db_session.flush()

    return sample_customer, order.id
