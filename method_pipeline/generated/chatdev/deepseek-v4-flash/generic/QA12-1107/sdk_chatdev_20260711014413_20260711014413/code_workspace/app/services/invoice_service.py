"""
Invoice service — create and manage invoices.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.enums import InvoiceStatus, OrderStatus
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.order_repo import OrderRepository
from app.schemas.invoice_schema import InvoiceResponse


class InvoiceService:
    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        order_repo: OrderRepository,
    ) -> None:
        self._invoice_repo = invoice_repo
        self._order_repo = order_repo

    async def create_invoice(
        self,
        order_id: str,
        billing_info: str,
        due_days: int = 30,
    ) -> InvoiceResponse:
        """Accountant creates invoice for accepted order (step 3)."""
        order = await self._order_repo.get_with_items(order_id)
        if order is None:
            raise ValueError("Order not found")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(f"Cannot invoice order in status {order.status.value}")

        # Check for existing invoice on this order
        existing = await self._invoice_repo.get_by_order(order_id)
        if existing is not None:
            raise ValueError(f"Order {order_id} already has an invoice ({existing.id})")

        now = datetime.now(timezone.utc)
        due_date = now + timedelta(days=due_days)

        invoice = await self._invoice_repo.create(
            order_id=order_id,
            customer_id=order.customer_id,
            billing_info=billing_info,
            total_amount=order.total_amount,
            currency=order.currency,
            issue_date=now,
            due_date=due_date,
            status=InvoiceStatus.ISSUED,
        )

        order.status = OrderStatus.INVOICED
        await self._order_repo.session.flush()

        return InvoiceResponse.model_validate(invoice)

    async def get_invoice(self, invoice_id: str) -> InvoiceResponse | None:
        invoice = await self._invoice_repo.get(invoice_id)
        if invoice is None:
            return None
        return InvoiceResponse.model_validate(invoice)

    async def list_invoices(
        self,
        status: InvoiceStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[InvoiceResponse], int]:
        invoices, total = await self._invoice_repo.list_by_status(
            status=status, skip=skip, limit=limit
        )
        return [InvoiceResponse.model_validate(inv) for inv in invoices], total
