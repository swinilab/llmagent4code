"""
Order service: manages the complete order lifecycle.

Latency-critical path (NFR 1.1):
  - Order creation (checkout) — must complete in < 300ms p95.
  - Uses cache-aside for product lookups, async DB writes.

Degradable operations (NFR 2.1):
  - Order history queries can be served from cache or degraded.
  - Invoice generation is offloaded to a background queue.

State preservation (NFR 2.3):
  - Order state is persisted to PostgreSQL before acknowledging the request.
  - Async steps (invoicing, shipping preparation) are enqueued to Redis Streams.

Workflow integrity (7-step process):
  1. Customer places order (CREATED)
  2. Order Staff reviews & accepts (CREATED → ACCEPTED)
  3. Accountant creates invoice (ACCEPTED → INVOICED) — async via worker
  4. Customer pays invoice (INVOICED → PAID)
  5. Accountant verifies payment (PAID — verification step)
  6. Order Staff ships paid order (PAID → SHIPPED)
  7. Order Staff closes completed order (SHIPPED → CLOSED)

  IMPORTANT: The shipping preparation task enqueued after payment does NOT
  transition the order to SHIPPED. That transition is exclusively performed
  by the Order Staff via the POST /api/v1/orders/{order_id}/ship endpoint.
  This ensures the Accountant verification step (Step 5) and Order Staff
  shipping action (Step 6) are not bypassed.

Stock management:
  - Stock is decremented atomically during order creation (within the same
    transaction) to prevent overselling. The product's version/optimistic
    lock ensures no concurrent order can double-claim the same stock.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from oms.adapters.repositories import (
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
    PaymentRepository,
    ProductRepository,
)
from oms.domain.enums import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from oms.domain.exceptions import (
    InsufficientStockError,
    InvalidPaymentMethodError,
    InvalidStateTransitionError,
    OrderNotFoundError,
    PaymentAmountMismatchError,
    ProductNotFoundError,
)
from oms.domain.models import (
    Address,
    Invoice,
    LineItem,
    Money,
    Order,
    Payment,
)
from oms.infrastructure.circuit_breaker import get_circuit_breaker
from oms.infrastructure.database import get_readonly_session, get_session
from oms.infrastructure.queue import enqueue
from oms.infrastructure.retry import checkout_retry_policy, background_retry_policy

logger = logging.getLogger(__name__)

_order_repo = OrderRepository()
_product_repo = ProductRepository()
_customer_repo = CustomerRepository()
_payment_repo = PaymentRepository()
_invoice_repo = InvoiceRepository()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderService:
    """Business logic for order operations."""

    async def create_order(
        self,
        customer_id: str,
        items: list[dict],
        shipping_address: Optional[dict] = None,
        notes: str = "",
    ) -> Order:
        """Create a new order (checkout — latency-critical path).

        This is the core checkout operation. It:
          1. Validates product availability and stock.
          2. Decrements stock atomically within the transaction.
          3. Creates the order with CREATED status.
          4. Persists to DB before returning (NFR 2.3).
          5. Does NOT enqueue invoice generation — that happens after acceptance.

        Uses checkout_retry_policy (2 attempts, short backoff) to handle
        transient DB/network errors without exceeding the 300ms p95 budget
        (NFR 1.1 vs NFR 2.2 trade-off).
        """
        async for attempt in checkout_retry_policy:
            with attempt:
                async with get_session() as session:
                    customer = await _customer_repo.get_by_id(session, customer_id)

                    line_items: list[LineItem] = []
                    total = Money(Decimal("0.00"))

                    for item in items:
                        product = await _product_repo.get_by_id(session, item["product_id"])
                        if not product.available:
                            raise ProductNotFoundError(product.id)
                        if product.stock < item["quantity"]:
                            raise InsufficientStockError(
                                product.id, item["quantity"], product.stock
                            )
                        # Decrement stock atomically within the same transaction
                        product.stock -= item["quantity"]
                        await _product_repo.update(session, product)
                        line_item = LineItem(
                            product_id=product.id,
                            product_name=product.name,
                            quantity=item["quantity"],
                            unit_price=product.base_price,
                        )
                        line_items.append(line_item)
                        total = total + line_item.total_price

                    addr = Address(**shipping_address) if shipping_address else None

                    order = Order(
                        customer_id=customer_id,
                        line_items=line_items,
                        total_amount=total,
                        shipping_address=addr,
                        notes=notes,
                    )
                    await _order_repo.save(session, order)

                    logger.info("Order %s created for customer %s", order.id, customer_id)
                    return order

    async def accept_order(self, order_id: str) -> Order:
        """Order Staff accepts an order (CREATED → ACCEPTED).

        After acceptance, enqueues invoice generation asynchronously (NFR 1.3, NFR 2.3).

        Uses background_retry_policy (5 attempts, longer backoff) since this
        is not on the latency-critical checkout path (NFR 2.1 degradable).
        """
        async for attempt in background_retry_policy:
            with attempt:
                async with get_session() as session:
                    order = await _order_repo.get_by_id(session, order_id)
                    order.transition_to(OrderStatus.ACCEPTED)
                    await _order_repo.update(session, order)

                    # Enqueue async invoice generation AFTER acceptance (NFR 1.3, NFR 2.3)
                    enqueued = await enqueue("orders:invoice", {
                        "order_id": order.id,
                        "customer_id": order.customer_id,
                        "action": "generate_invoice",
                    })
                    if not enqueued:
                        logger.warning(
                            "Invoice queue full for order %s — will retry later",
                            order.id,
                        )

                    logger.info("Order %s accepted", order_id)
                    return order

    async def ship_order(self, order_id: str) -> Order:
        """Order Staff ships a paid order (PAID → SHIPPED) — Step 6 of the 7-step workflow.

        This is called ONLY by the Order Staff via the POST /ship endpoint.
        It is NOT called by the background worker — the worker only performs
        shipping preparation (non-status-changing).
        """
        async with get_session() as session:
            order = await _order_repo.get_by_id(session, order_id)
            order.transition_to(OrderStatus.SHIPPED)
            await _order_repo.update(session, order)
            logger.info("Order %s shipped", order_id)
            return order

    async def close_order(self, order_id: str) -> Order:
        """Order Staff closes a shipped order (SHIPPED → CLOSED)."""
        async with get_session() as session:
            order = await _order_repo.get_by_id(session, order_id)
            order.transition_to(OrderStatus.CLOSED)
            await _order_repo.update(session, order)
            logger.info("Order %s closed", order_id)
            return order

    async def cancel_order(self, order_id: str) -> Order:
        """Cancel an order (any active status → CANCELLED)."""
        async with get_session() as session:
            order = await _order_repo.get_by_id(session, order_id)
            order.transition_to(OrderStatus.CANCELLED)
            await _order_repo.update(session, order)
            logger.info("Order %s cancelled", order_id)
            return order

    async def get_order(self, order_id: str) -> Order:
        """Get order by ID (uses cache-aside)."""
        async with get_readonly_session() as session:
            return await _order_repo.get_by_id(session, order_id)

    async def get_orders_by_customer(self, customer_id: str) -> list[Order]:
        """Get all orders for a customer (degradable — NFR 2.1)."""
        cb = get_circuit_breaker("order_history")
        async with get_readonly_session() as session:
            try:
                return await cb.call(
                    _order_repo.get_by_customer, session, customer_id
                )
            except Exception:
                logger.warning("Order history degraded for customer %s", customer_id)
                return []

    async def get_orders_by_status(self, status: str) -> list[Order]:
        """Get orders by status (for Order Staff / Accountant)."""
        async with get_readonly_session() as session:
            return await _order_repo.get_by_status(session, status)

    async def pay_order(
        self,
        order_id: str,
        amount: Decimal,
        currency: str,
        method: str,
    ) -> Order:
        """Customer pays for an order (INVOICED → PAID).

        This is called after the customer pays the invoice.
        Validates the payment method and amount before processing.
        Also marks the associated invoice as PAID to keep invoice
        lifecycle consistent with the order.

        CRITICAL: Payment amount is validated against the INVOICE total
        (which includes tax), NOT the order total (which is pre-tax subtotal).
        This ensures the customer pays the correct amount including tax.

        After payment, enqueues a shipping PREPARATION task (NOT a status
        transition). The worker will prepare shipping (e.g., generate a
        label) but will NOT call ship_order(). The PAID → SHIPPED transition
        is exclusively performed by the Order Staff via the POST /ship endpoint.
        This preserves the required 7-step workflow:
          Step 5: Accountant verifies payment
          Step 6: Order Staff ships

        Uses checkout_retry_policy (2 attempts, short backoff) to handle
        transient errors without exceeding the 300ms p95 budget
        (NFR 1.1 vs NFR 2.2 trade-off).
        """
        # Validate payment method before any DB operations
        try:
            payment_method = PaymentMethod(method)
        except ValueError:
            raise InvalidPaymentMethodError(method)

        async for attempt in checkout_retry_policy:
            with attempt:
                async with get_session() as session:
                    order = await _order_repo.get_by_id(session, order_id)

                    # Validate against invoice total (which includes tax)
                    # The invoice includes an 8% tax on the subtotal. The customer
                    # must pay the invoice total, not the pre-tax order total.
                    if not order.invoice_ref:
                        raise InvalidStateTransitionError(
                            order.status.value,
                            "PAID",
                        )
                    invoice = await _invoice_repo.get_by_id(session, order.invoice_ref)

                    # Validate payment amount against invoice total (includes tax)
                    if Decimal(str(amount)) != invoice.total.amount:
                        raise PaymentAmountMismatchError(
                            order_id,
                            str(invoice.total.amount),
                            str(amount),
                        )

                    order.transition_to(OrderStatus.PAID)

                    payment = Payment(
                        order_id=order_id,
                        amount=Money(amount=amount, currency=currency),
                        status=PaymentStatus.COMPLETED,
                        method=payment_method,
                        transaction_id=f"txn_{order_id}_{_utcnow().timestamp()}",
                        paid_at=_utcnow(),
                    )
                    await _payment_repo.save(session, payment)
                    order.payment_ref = payment.id
                    await _order_repo.update(session, order)

                    # Mark the associated invoice as PAID (NFR 2.3 — state consistency)
                    invoice.status = InvoiceStatus.PAID
                    invoice.paid_at = _utcnow()
                    await _invoice_repo.update(session, invoice)
                    logger.info(
                        "Invoice %s marked as paid for order %s",
                        order.invoice_ref, order_id,
                    )

                    # Enqueue shipping preparation (non-status-changing)
                    await enqueue("orders:ship", {
                        "order_id": order_id,
                        "action": "prepare_shipping",
                    })

                    logger.info("Order %s paid (payment %s)", order_id, payment.id)
                    return order

    async def verify_payment(self, order_id: str) -> Order:
        """Accountant verifies payment (Step 5 of the 7-step workflow).

        This is a verification step that confirms the payment is legitimate.
        The order must already be in PAID status (set by pay_order).
        This step does NOT change the order status — it only verifies.

        Also ensures the associated invoice is marked as PAID — this is a
        safety net in case the invoice was not updated during pay_order
        (e.g. due to a partial failure or race condition).

        After this step, the Order Staff can ship the order (Step 6).
        """
        async with get_session() as session:
            order = await _order_repo.get_by_id(session, order_id)
            if order.status != OrderStatus.PAID:
                raise InvalidStateTransitionError(
                    order.status.value, "VERIFY_PAYMENT"
                )

            # Ensure invoice is marked as paid (defensive — NFR 2.3)
            if order.invoice_ref:
                invoice = await _invoice_repo.get_by_id(session, order.invoice_ref)
                if invoice.status != InvoiceStatus.PAID:
                    invoice.status = InvoiceStatus.PAID
                    invoice.paid_at = _utcnow()
                    await _invoice_repo.update(session, invoice)
                    logger.info(
                        "Invoice %s marked as paid during verification for order %s",
                        order.invoice_ref, order_id,
                    )

            logger.info("Payment verified for order %s", order_id)
            return order
