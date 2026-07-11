"""Pytest fixtures — async session, test client, and test data setup."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

# Use in-memory SQLite with WAL mode for test isolation and speed
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)


@event.listens_for(test_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()


TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def sample_customer(client: AsyncClient) -> dict[str, Any]:
    resp = await client.post(
        "/v1/customers",
        json={
            "name": "Alice Johnson",
            "address": "123 Elm St",
            "phone": "+1-555-0100",
            "banking_details": "Bank of Test, acct 12345",
            "role": "customer",
        },
    )
    assert resp.status_code == 201, f"Failed to create customer: {resp.text}"
    return resp.json()


@pytest_asyncio.fixture
async def sample_product(client: AsyncClient) -> dict[str, Any]:
    resp = await client.post(
        "/v1/products",
        json={
            "description": "Widget A",
            "base_price": "29.99",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, f"Failed to create product: {resp.text}"
    return resp.json()


@pytest_asyncio.fixture
async def sample_order(
    client: AsyncClient,
    sample_customer: dict[str, Any],
    sample_product: dict[str, Any],
) -> dict[str, Any]:
    resp = await client.post(
        "/v1/orders",
        json={
            "customer_id": sample_customer["id"],
            "line_items": [
                {
                    "product_id": sample_product["id"],
                    "quantity": 2,
                    "unit_price": "29.99",
                    "subtotal": "59.98",
                }
            ],
        },
    )
    assert resp.status_code == 201, f"Failed to create order: {resp.text}"
    return resp.json()