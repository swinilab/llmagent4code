"""
Tests for InvoiceService — invoice lifecycle.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.models.orm_models import Customer, Product
from oms_backend.schemas.domain import InvoiceCreate, InvoiceIssue, OrderCreate, LineItemCreate
from oms_backend.services.invoice import InvoiceService
from oms_backend.services.order import OrderService


@pytest.mark.asyncio
async def test_invoice_create_from_order(db_session: AsyncSession, sample_customer: Customer, sample_product: Product):
    """Accountant creates a draft invoice from an accepted order."""
    # First create and accept an order
    order_svc = OrderService(db_session)
    order_data = OrderCreate(
        customer_id=sample_customer.id,
        items=[
            LineItemCreate(
                product_id=sample_product.id,
                quantity=1,
                tax_rate=Decimal("0.0825"),
            )
        ],
    )
    order = await order_svc.create(order_data)
    await order_svc.accept(order.id)

    # Create invoice
    inv_svc = InvoiceService(db_session)
    inv_data = InvoiceCreate(
        order_id=order.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=14),
    )
    invoice = await inv_svc.create_from_order(order.id, inv_data)

    assert invoice.code.startswith("INV-")
    assert invoice.status == "draft"
    assert invoice.total_amount == order.total_amount

    # Order should now be 'invoiced'
    await db_session.refresh(order)
    assert order.status == "invoiced"
    assert order.invoice_id == invoice.id


@pytest.mark.asyncio
async def test_invoice_issue(db_session: AsyncSession, sample_customer: Customer, sample_product: Product):
    """Accountant issues a draft invoice."""
    order_svc = OrderService(db_session)
    order_data = OrderCreate(
        customer_id=sample_customer.id,
        items=[
            LineItemCreate(
                product_id=sample_product.id,
                quantity=1,
                tax_rate=Decimal("0"),
            )
        ],
    )
    order = await order_svc.create(order_data)
    await order_svc.accept(order.id)

    inv_svc = InvoiceService(db_session)
    inv_data = InvoiceCreate(
        order_id=order.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=7),
    )
    invoice = await inv_svc.create_from_order(order.id, inv_data)

    # Issue the invoice
    issued = await inv_svc.issue(
        invoice.id,
        InvoiceIssue(issue_date=date.today(), due_date=date.today() + timedelta(days=14)),
    )
    assert issued.status == "issued"


@pytest.mark.asyncio
async def test_invoice_cannot_create_for_unaccepted_order(db_session: AsyncSession, sample_customer: Customer, sample_product: Product):
    """Only accepted orders can be invoiced."""
    order_svc = OrderService(db_session)
    order_data = OrderCreate(
        customer_id=sample_customer.id,
        items=[
            LineItemCreate(
                product_id=sample_product.id,
                quantity=1,
                tax_rate=Decimal("0"),
            )
        ],
    )
    order = await order_svc.create(order_data)

    inv_svc = InvoiceService(db_session)
    inv_data = InvoiceCreate(
        order_id=order.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=7),
    )
    with pytest.raises(ValueError, match="must be accepted"):
        await inv_svc.create_from_order(order.id, inv_data)
