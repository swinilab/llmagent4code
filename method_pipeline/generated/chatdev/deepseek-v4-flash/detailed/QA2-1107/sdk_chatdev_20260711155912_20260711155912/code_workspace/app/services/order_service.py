"""
Order service: business logic for order lifecycle management.

Criticality: CORE (NFR 2.1) — checkout must remain available under load.
Recovery: Retry on transient DB errors (NFR 2.2); manual intervention
required for business-rule violations (e.g., invalid state transition).
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbox import OutboxRepository
from app.adapters.repositories import (
    CustomerRepository,
    InvoiceRepository,
    OrderLineItemRepository,
    OrderRepository,
    ProductRepository,
)
from app.domain.enums import InvoiceStatus, OrderStatus
from app.domain.models import Order, OrderLineItem
from app.domain.schemas import OrderCreate
from app.domain.state_machine import (
    TRANSITION_TIMESTAMP_FIELDS,
    TransitionEvent,
    apply_transition,
)

logger = logging.getLogger(__name__)


class OrderService:
    """Encapsulates order business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_repo = OrderRepository(session)
        self._line_item_repo = OrderLineItemRepository(session)
        self._customer_repo = CustomerRepository(session)
        self._product_repo = ProductRepository(session)
        self._invoice_repo = InvoiceRepository(session)
        self._outbox_repo = OutboxRepository(session)

    async def create_order(self, data: OrderCreate) -> Order:
        """Create a new order with line items (CORE workflow step 1)."""
        # Validate customer exists
        customer = await self._customer_repo.get(data.customer_id)
        if customer is None:
            raise ValueError(f"Customer {data.customer_id} not found")

        # Create the order
        order = Order(
            customer_id=data.customer_id,
            status=OrderStatus.CREATED,
            total_amount=0.0,
            currency=data.currency,
        )
        order = await self._order_repo.create(order)

        # Create line items and compute total
        total = 0.0
        for item_data in data.line_items:
            product = await self._product_repo.get(item_data.product_id)
            if product is None:
                raise ValueError(f"Product {item_data.product_id} not found")
            if not product.available:
                raise ValueError(f"Product {product.id} is not available")

            line_item = OrderLineItem(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                currency=item_data.currency,
            )
            await self._line_item_repo.create(line_item)
            total += item_data.unit_price * item_data.quantity

        # Update order total
        order.total_amount = round(total, 2)
        await self._session.flush()

        # Write outbox message (same transaction)
        await self._outbox_repo.add_message(
            aggregate_type="order",
            aggregate_id=str(order.id),
            event_type="order.created",
            payload={
                "order_id": str(order.id),
                "customer_id": str(order.customer_id),
                "status": OrderStatus.CREATED.value,
                "total_amount": order.total_amount,
            },
        )

        logger.info("Order %s created for customer %s", order.id, data.customer_id)
        return order

    async def transition_order(
        self,
        order_id: uuid.UUID,
        event: TransitionEvent,
        invoice_ref: str | None = None,
    ) -> Order:
        """
        Apply a state transition to an order.

        This is the core state-change method used by all workflow steps.
        It enforces the state machine, updates the status with optimistic
        locking, records the transition timestamp, and writes an outbox
        event — all in a single database transaction.

        When cancelling an order that has an associated invoice, the
        invoice status is also updated to CANCELLED (fixing the dead-code
        issue where InvoiceRepository.update_status() was never called).

        Args:
            order_id: The order to transition.
            event: The transition event to apply.
            invoice_ref: Optional invoice reference to set on the order
                         (used when transitioning ACCEPTED -> INVOICED).
        """
        order = await self._order_repo.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")

        # Compute the new status via the state machine
        new_status = apply_transition(order.status, event)

        # Determine the timestamp field for this transition
        timestamp_field = TRANSITION_TIMESTAMP_FIELDS.get(event)

        # Persist with optimistic locking — pass invoice_ref if provided
        updated = await self._order_repo.update_status(
            order_id=order_id,
            new_status=new_status,
            current_version=order.version,
            timestamp_field=timestamp_field,
            invoice_ref=invoice_ref,
        )
        if updated is None:
            raise ValueError(
                f"Optimistic lock conflict on order {order_id}. "
                f"Reload and retry."
            )

        # If cancelling an order that has an invoice_ref, cancel the invoice too
        if event == TransitionEvent.CANCEL and order.invoice_ref:
            try:
                invoice_id = uuid.UUID(order.invoice_ref)
                invoice = await self._invoice_repo.get(invoice_id)
                if invoice is not None and invoice.status != InvoiceStatus.CANCELLED:
                    cancelled_inv = await self._invoice_repo.update_status(
                        invoice_id=invoice_id,
                        new_status=InvoiceStatus.CANCELLED,
                        current_version=invoice.version,
                    )
                    if cancelled_inv is None:
                        logger.warning(
                            "Optimistic lock conflict cancelling invoice %s for order %s",
                            invoice_id,
                            order_id,
                        )
                    else:
                        logger.info(
                            "Invoice %s cancelled for order %s",
                            invoice_id,
                            order_id,
                        )
            except (ValueError, AttributeError) as exc:
                logger.warning(
                    "Could not cancel invoice for order %s: %s",
                    order_id,
                    exc,
                )

        # Write outbox message (same transaction)
        await self._outbox_repo.add_message(
            aggregate_type="order",
            aggregate_id=str(order_id),
            event_type=f"order.{event.value}",
            payload={
                "order_id": str(order_id),
                "from_status": order.status.value,
                "to_status": new_status.value,
                "event": event.value,
            },
        )

        logger.info(
            "Order %s transitioned: %s -> %s (event=%s)",
            order_id,
            order.status.value,
            new_status.value,
            event.value,
        )
        return updated

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        """Retrieve an order by ID."""
        return await self._order_repo.get(order_id)

    async def list_all_orders(self) -> list[Order]:
        """List all orders."""
        return list(await self._order_repo.list_all())

    async def list_orders_by_customer(self, customer_id: uuid.UUID) -> list[Order]:
        """List all orders for a customer."""
        return list(await self._order_repo.list_by_customer(customer_id))

    async def list_orders_by_status(self, status: OrderStatus) -> list[Order]:
        """List all orders in a given status."""
        return list(await self._order_repo.list_by_status(status))
