"""
Tests for OrderService — covers complete order lifecycle.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.models.orm_models import Customer, Order, Product, LineItem
from oms_backend.schemas.domain import OrderCreate, OrderAccept, LineItemCreate, OrderShip, OrderClose
from oms_backend.services.order import OrderService


@pytest_asyncio.fixture
async def order_service(db_session: AsyncSession) -> OrderService:
    return OrderService(db_session)


@pytest_asyncio.fixture
async def chain(db_session: AsyncSession, sample_customer: Customer, sample_product: Product):
    """Returns (customer, product) for order tests."""
    return sample_customer, sample_product


@pytest.mark.asyncio
async def test_order_lifecycle_full(
    db_session: AsyncSession,
    chain,
):
    """
    Test the complete order lifecycle:
    create → accept → cancel → restore stock
    """
    customer, product = chain
    svc = OrderService(db_session)

    data = OrderCreate(
        customer_id=customer.id,
        items=[
            LineItemCreate(
                product_id=product.id,
                quantity=2,
                tax_rate=Decimal("0.0825"),
            )
        ],
        notes="Test order",
    )
    order = await svc.create(data)

    assert order.id is not None
    assert order.code.startswith("ORD-")
    assert order.status == "pending"
    assert order.total_amount == Decimal("108.2398")  # 2 * 49.99 * 1.0825

    # Stock should be decremented
    await db_session.refresh(product)
    assert product.stock_qty == 98

    # Accept order
    accepted = await svc.accept(order.id, OrderAccept(notes="Looks good"))
    assert accepted.status == "accepted"
    assert accepted.accepted_at is not None

    # Cancel order
    cancelled = await svc.cancel(order.id)
    assert cancelled.status == "cancelled"

    # Stock should be restored
    await db_session.refresh(product)
    assert product.stock_qty == 100


@pytest.mark.asyncio
async def test_order_cannot_accept_non_pending(db_session: AsyncSession, chain):
    """Only pending orders can be accepted."""
    customer, product = chain
    svc = OrderService(db_session)

    data = OrderCreate(
        customer_id=customer.id,
        items=[
            LineItemCreate(
                product_id=product.id,
                quantity=1,
                tax_rate=Decimal("0"),
            )
        ],
    )
    order = await svc.create(data)
    await svc.accept(order.id)

    with pytest.raises(ValueError, match="only pending"):
        await svc.accept(order.id)


@pytest.mark.asyncio
async def test_order_ship_only_paid(db_session: AsyncSession, chain):
    """Only paid orders can be shipped."""
    customer, product = chain
    svc = OrderService(db_session)

    data = OrderCreate(
        customer_id=customer.id,
        items=[
            LineItemCreate(
                product_id=product.id,
                quantity=1,
                tax_rate=Decimal("0"),
            )
        ],
    )
    order = await svc.create(data)
    await svc.accept(order.id)

    with pytest.raises(ValueError, match="only paid"):
        await svc.ship(order.id, OrderShip(tracking_number="1Z123"))


@pytest.mark.asyncio
async def test_order_cannot_update_accepted_order(db_session: AsyncSession, chain):
    """Non-pending orders cannot be updated."""
    customer, product = chain
    svc = OrderService(db_session)

    data = OrderCreate(
        customer_id=customer.id,
        items=[
            LineItemCreate(
                product_id=product.id,
                quantity=1,
                tax_rate=Decimal("0"),
            )
        ],
    )
    order = await svc.create(data)
    await svc.accept(order.id)

    from oms_backend.schemas.domain import OrderUpdate
    with pytest.raises(ValueError, match="Cannot update"):
        await svc.update(order.id, OrderUpdate(notes="Updated notes"))


@pytest.mark.asyncio
async def test_order_close_after_ship(db_session: AsyncSession, chain):
    """Order can be closed after shipping."""
    customer, product = chain
    svc = OrderService(db_session)

    data = OrderCreate(
        customer_id=customer.id,
        items=[
            LineItemCreate(
                product_id=product.id,
                quantity=1,
                tax_rate=Decimal("0"),
            )
        ],
    )
    order = await svc.create(data)
    await svc.accept(order.id)

    # Manually update order to shipped status for testing (in real flow via invoice+payment)
    from oms_backend.repositories.entities import OrderRepository
    repo = OrderRepository(db_session)
    await repo.update_status(order.id, "paid")

    shipped = await svc.ship(order.id, OrderShip(tracking_number="1Z999"))
    assert shipped.status == "shipped"

    closed = await svc.close(order.id, OrderClose(notes="Delivered confirmed"))
    assert closed.status == "closed"
