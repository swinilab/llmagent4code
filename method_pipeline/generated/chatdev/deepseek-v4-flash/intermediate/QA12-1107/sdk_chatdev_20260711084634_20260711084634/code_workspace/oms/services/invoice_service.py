"""
Invoice service: invoice generation and management.

Invoice creation is triggered asynchronously via the task queue (NFR 1.3).
It is not on the latency-critical checkout path and can be degraded (NFR 2.1).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from oms.adapters.repositories import (
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
)
from oms.domain.enums import InvoiceStatus, OrderStatus
from oms.domain.models import Address, Invoice, Money
from oms.infrastructure.circuit_breaker import get_circuit_breaker
from oms.infrastructure.database import get_readonly_session, get_session

logger = logging.getLogger(__name__)

_invoice_repo = InvoiceRepository()
_order_repo = OrderRepository()
_customer_repo = CustomerRepository()

TAX_RATE = Decimal("0.08")  # 8% tax


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InvoiceService:
    """Business logic for invoice operations."""

    async def generate_invoice(self, order_id: str) -> Invoice:
        """Generate an invoice for an accepted order.

        This is called by the background worker after the order is accepted.
        It transitions the order from ACCEPTED to INVOICED.
        """
        async with get_session() as session:
            order = await _order_repo.get_by_id(session, order_id)
            if order.status != OrderStatus.ACCEPTED:
                logger.warning(
                    "Cannot invoice order %s: status is %s",
                    order_id, order.status,
                )
                raise ValueError(
                    f"Cannot invoice order {order_id}: status is {order.status}"
                )

            customer = await _customer_repo.get_by_id(session, order.customer_id)

            subtotal = order.total_amount
            tax = Money(amount=(subtotal.amount * TAX_RATE).quantize(Decimal("0.01")),
                        currency=subtotal.currency)
            total = Money(amount=subtotal.amount + tax.amount, currency=subtotal.currency)

            invoice = Invoice(
                order_id=order_id,
                customer_id=order.customer_id,
                billing_address=customer.address,
                line_items=order.line_items,
                subtotal=subtotal,
                tax=tax,
                total=total,
                status=InvoiceStatus.ISSUED,
                issue_date=_utcnow(),
                due_date=_utcnow() + timedelta(days=30),
            )
            await _invoice_repo.save(session, invoice)

            # Update order status and invoice ref
            order.transition_to(OrderStatus.INVOICED)
            order.invoice_ref = invoice.id
            await _order_repo.update(session, order)

            logger.info("Invoice %s generated for order %s", invoice.id, order_id)
            return invoice

    async def get_invoice(self, invoice_id: str) -> Invoice:
        """Get an invoice by ID."""
        async with get_readonly_session() as session:
            return await _invoice_repo.get_by_id(session, invoice_id)

    async def get_invoices_by_order(self, order_id: str) -> list[Invoice]:
        """Get invoices for an order (degradable — NFR 2.1)."""
        cb = get_circuit_breaker("invoice_history")
        async with get_readonly_session() as session:
            try:
                return await cb.call(
                    _invoice_repo.get_by_order, session, order_id
                )
            except Exception:
                logger.warning("Invoice history degraded for order %s", order_id)
                return []

    async def mark_invoice_paid(self, invoice_id: str) -> Invoice:
        """Mark an invoice as paid."""
        async with get_session() as session:
            invoice = await _invoice_repo.get_by_id(session, invoice_id)
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = _utcnow()
            await _invoice_repo.update(session, invoice)
            logger.info("Invoice %s marked as paid", invoice_id)
            return invoice
