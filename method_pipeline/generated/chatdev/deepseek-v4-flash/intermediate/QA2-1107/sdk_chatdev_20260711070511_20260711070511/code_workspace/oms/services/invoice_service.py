"""
Invoice service – handles invoice creation and status management.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from oms.models.entities import InvoiceModel
from oms.models.enums import InvoiceStatus, OrderStatus
from oms.repositories.invoice_repo import InvoiceRepository
from oms.repositories.order_repo import OrderRepository
from oms.schemas.invoice import InvoiceCreate

logger = logging.getLogger(__name__)


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvoiceRepository(db)
        self.order_repo = OrderRepository(db)

    def create_invoice(self, data: InvoiceCreate) -> InvoiceModel:
        """Create an invoice for an accepted order. Critical operation."""
        order = self.order_repo.get(data.order_id)
        if not order:
            raise ValueError(f"Order {data.order_id} not found")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(
                f"Cannot invoice order in status {order.status.value}"
            )

        # Prevent duplicate invoices for the same order
        existing_invoices = self.repo.get_by_order(data.order_id)
        if existing_invoices:
            raise ValueError(
                f"Order {data.order_id} already has {len(existing_invoices)} invoice(s)"
            )

        # Validate invoice amount matches order total (Fix 3)
        if data.total_amount != order.total_amount:
            raise ValueError(
                f"Invoice amount {data.total_amount} does not match "
                f"order total {order.total_amount}"
            )

        # Validate invoice currency matches order currency (Fix 3)
        if data.currency != order.currency:
            raise ValueError(
                f"Invoice currency {data.currency} does not match "
                f"order currency {order.currency}"
            )

        invoice = InvoiceModel(
            order_id=data.order_id,
            billing_name=data.billing_name,
            billing_address=data.billing_address,
            total_amount=data.total_amount,
            currency=data.currency,
            status=InvoiceStatus.ISSUED,
            issue_date=datetime.now(timezone.utc),
            due_date=data.due_date or (datetime.now(timezone.utc) + timedelta(days=30)),
        )
        self.repo.create(invoice)

        # Transition order to INVOICED using OrderRepository's optimistic lock
        updated_order = self.order_repo.update_with_optimistic_lock(
            order.id,
            {"status": OrderStatus.INVOICED, "invoice_ref": invoice.id},
            order.version,
        )
        if updated_order is None:
            raise ValueError(
                f"Concurrent modification on order {order.id} during invoice creation"
            )

        # Outbox for order status transition
        self.repo.write_outbox(
            aggregate_type="order",
            aggregate_id=data.order_id,
            event_type="order.invoiced",
            payload={
                "order_id": data.order_id,
                "previous_status": OrderStatus.ACCEPTED.value,
                "new_status": OrderStatus.INVOICED.value,
                "invoice_id": invoice.id,
            },
        )

        # Outbox for invoice
        self.repo.write_outbox(
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            event_type="invoice.created",
            payload={
                "invoice_id": invoice.id,
                "order_id": invoice.order_id,
                "total_amount": invoice.total_amount,
                "status": invoice.status.value,
            },
        )
        self.db.commit()
        logger.info("Invoice %s created for order %s", invoice.id, data.order_id)
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[InvoiceModel]:
        return self.repo.get(invoice_id)

    def list_by_order(self, order_id: str) -> List[InvoiceModel]:
        return self.repo.get_by_order(order_id)

    def list_all(self, skip: int = 0, limit: int = 100) -> List[InvoiceModel]:
        return self.repo.list_all(skip, limit)
