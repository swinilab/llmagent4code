"""Order service: business logic for the complete order lifecycle.

Latency classification (NFR 1.1):
  - Checkout-critical (p95 ≤ 300ms): place_order (cart → order submission)
  - Back-office (p95 ≤ 1s): accept, invoice, pay, verify, ship, close
    Relaxation justified: these are staff/accountant operations, not
    customer-facing. They involve human-in-the-loop delays (seconds to
    minutes) so sub-second API response is more than adequate.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from app.domain.enums import InvoiceStatus, OrderStatus, PaymentMethod, PaymentStatus
from app.domain.models import Invoice, LineItem, Order, Payment
from app.domain.state_machine import IllegalTransitionError, validate_transition
from app.infrastructure.cache import invalidate_product_cache, invalidate_search_cache
from app.infrastructure.circuit_breaker import (
    CircuitBreakerOpenError,
    payment_gateway_cb,
    shipping_api_cb,
)
from app.infrastructure.idempotency import (
    get_idempotent_response,
    store_idempotent_response,
)
from app.infrastructure.messaging import publish_work
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.orm_models import InvoiceModel, OrderModel, PaymentModel

logger = logging.getLogger(__name__)


class OrderService:
    """Orchestrates the order lifecycle with transaction boundaries."""

    def __init__(
        self,
        order_repo: OrderRepository,
        product_repo: ProductRepository,
        payment_repo: PaymentRepository,
        invoice_repo: InvoiceRepository,
    ) -> None:
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._payment_repo = payment_repo
        self._invoice_repo = invoice_repo

    async def place_order(
        self, customer_id: UUID, line_items_data: list[dict[str, Any]]
    ) -> Order:
        """Place a new order (checkout-critical path).

        This is the core checkout operation subject to NFR 1.1's 300ms p95 target.

        Stock is atomically decremented at placement time to prevent overselling.
        On concurrent requests, the database-level guard (WHERE stock_available >= quantity)
        ensures only one succeeds; the other gets a contention error.
        """
        # Build line items with price lookup
        line_items: list[LineItem] = []
        subtotal = Decimal("0.00")
        for item_data in line_items_data:
            product_id = UUID(item_data["product_id"])
            quantity = int(item_data["quantity"])

            product = await self._product_repo.get_by_id_cached(product_id)
            if product is None:
                raise ValueError(f"Product not found: {product_id}")
            if product.stock_available < quantity:
                raise ValueError(f"Insufficient stock for product: {product.name}")

            # Atomically decrement stock (prevents concurrent overselling)
            updated_product = await self._product_repo.decrement_stock(
                product_id, quantity
            )
            if updated_product is None:
                raise ValueError(
                    f"Stock contention for product: {product.name} — "
                    f"insufficient stock at commit time"
                )

            # Invalidate product cache so subsequent reads see the new stock level
            await invalidate_product_cache(str(product_id))

            unit_price = product.base_price
            total_price = unit_price * quantity
            line_items.append(
                LineItem(
                    product_id=product_id,
                    product_name=product.name,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                )
            )
            subtotal += total_price

        tax_amount = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"))  # 8% tax
        total_amount = subtotal + tax_amount

        order = Order(
            customer_id=customer_id,
            line_items=line_items,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status=OrderStatus.CREATED,
        )
        # Persist
        order_model = OrderModel(
            id=order.id,
            customer_id=order.customer_id,
            line_items=self._order_repo.serialize_json_list(line_items),
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            status=order.status,
            version=order.version,
        )
        await self._order_repo.save(order_model)

        # Publish deferrable work: notification to order staff
        await publish_work(
            "new_order_notification",
            {"order_id": str(order.id), "customer_id": str(customer_id)},
        )

        logger.info("Order placed: id=%s, total=%s", order.id, total_amount)
        return order

    async def accept_order(self, order_id: UUID) -> Order:
        """Order Staff accepts an order (back-office, p95 ≤ 1s)."""
        order_model = await self._order_repo.get_by_id(order_id)
        if order_model is None:
            raise ValueError(f"Order not found: {order_id}")

        new_status = validate_transition(order_model.status, "accept")
        now = datetime.utcnow()

        updated = await self._order_repo.update_with_version_check(
            order_id,
            {"status": new_status, "accepted_at": now, "updated_at": now},
            order_model.version,
        )
        logger.info("Order accepted: id=%s", order_id)
        return self._model_to_domain(updated)

    async def create_invoice(
        self,
        order_id: UUID,
        customer_name: str,
        customer_address: str,
        billing_info: str,
    ) -> Invoice:
        """Accountant creates an invoice for an accepted order (back-office)."""
        order_model = await self._order_repo.get_by_id(order_id)
        if order_model is None:
            raise ValueError(f"Order not found: {order_id}")

        new_status = validate_transition(order_model.status, "invoice")
        now = datetime.utcnow()

        # Create invoice domain model
        invoice = Invoice(
            order_id=order_id,
            customer_name=customer_name,
            customer_address=customer_address,
            billing_info=billing_info,
            subtotal=order_model.subtotal,
            tax_amount=order_model.tax_amount,
            total_amount=order_model.total_amount,
            status=InvoiceStatus.ISSUED,
            issue_date=now,
            due_date=now + timedelta(days=30),
        )

        # Persist as ORM model
        invoice_model = InvoiceModel(
            id=invoice.id,
            order_id=invoice.order_id,
            customer_name=invoice.customer_name,
            customer_address=invoice.customer_address,
            billing_info=invoice.billing_info,
            subtotal=invoice.subtotal,
            tax_amount=invoice.tax_amount,
            total_amount=invoice.total_amount,
            status=invoice.status,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
        )
        await self._invoice_repo.save(invoice_model)

        # Update order status to INVOICED
        await self._order_repo.update_with_version_check(
            order_id,
            {
                "status": new_status,
                "invoice_ref": invoice.id,
                "invoiced_at": now,
                "updated_at": now,
            },
            order_model.version,
        )

        logger.info("Invoice created: id=%s, order=%s", invoice.id, order_id)
        return invoice

    async def submit_payment(
        self, order_id: UUID, amount: Decimal, method: str, idempotency_key: str
    ) -> Payment:
        """Customer pays invoice (checkout-critical, p95 ≤ 300ms).

        Includes idempotency handling and circuit breaker for payment gateway.
        """
        # Check idempotency first
        cached_response = await get_idempotent_response(idempotency_key)
        if cached_response is not None:
            logger.info("Idempotent payment return: key=%s", idempotency_key)
            return Payment(**cached_response)

        # Check existing payment with same idempotency key in DB
        existing_payment = await self._payment_repo.get_by_idempotency_key(
            idempotency_key
        )
        if existing_payment is not None:
            logger.info("Duplicate payment detected: key=%s", idempotency_key)
            payment = Payment(
                id=existing_payment.id,
                order_id=existing_payment.order_id,
                amount=existing_payment.amount,
                currency=existing_payment.currency,
                status=existing_payment.status,
                method=existing_payment.method,
                idempotency_key=existing_payment.idempotency_key,
                timestamp=existing_payment.timestamp,
            )
            await store_idempotent_response(idempotency_key, payment.model_dump())
            return payment

        order_model = await self._order_repo.get_by_id(order_id)
        if order_model is None:
            raise ValueError(f"Order not found: {order_id}")

        new_status = validate_transition(order_model.status, "pay")

        # Call payment gateway through circuit breaker
        payment_method = PaymentMethod(method)

        async def call_payment_gateway() -> bool:
            # Simulated payment gateway call
            # In production, this would be an HTTP call to a payment provider
            return True

        try:
            payment_success = await payment_gateway_cb.call(call_payment_gateway)
        except CircuitBreakerOpenError:
            logger.error(
                "Payment gateway circuit breaker OPEN for order %s", order_id
            )
            raise

        now = datetime.utcnow()
        payment = Payment(
            order_id=order_id,
            amount=amount,
            status=PaymentStatus.COMPLETED if payment_success else PaymentStatus.FAILED,
            method=payment_method,
            idempotency_key=idempotency_key,
            timestamp=now,
        )

        payment_model = PaymentModel(
            id=payment.id,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            method=payment.method,
            idempotency_key=payment.idempotency_key,
            timestamp=payment.timestamp,
        )
        # Persist the payment record before any status update
        await self._payment_repo.save(payment_model)

        if payment_success:
            await self._order_repo.update_with_version_check(
                order_id,
                {
                    "status": new_status,
                    "paid_at": now,
                    "updated_at": now,
                },
                order_model.version,
            )
        # Store idempotency response
        await store_idempotent_response(idempotency_key, payment.model_dump())

        logger.info(
            "Payment processed: id=%s, order=%s, status=%s",
            payment.id,
            order_id,
            payment.status,
        )
        return payment

    async def verify_payment(
        self, order_id: UUID, accountant_id: Optional[UUID] = None
    ) -> Order:
        """Accountant verifies payment (back-office).

        Performs a reconciliation check: confirms the payment record exists,
        matches the order total, and marks the verification event with
        accountant context. In production this would cross-reference with
        the payment gateway's settlement report.

        Note: This is a read-only validation — it does NOT change the order
        status. The order remains PAID until ship_order transitions it to
        SHIPPED. Therefore we raise ValueError (not IllegalTransitionError)
        because no state transition is being attempted.

        Args:
            order_id: The order to verify.
            accountant_id: Optional UUID of the accountant performing verification.

        Raises:
            ValueError: If order is not found, or if order status is not PAID,
                or if payment record is missing/invalid.
        """
        order_model = await self._order_repo.get_by_id(order_id)
        if order_model is None:
            raise ValueError(f"Order not found: {order_id}")

        if order_model.status != OrderStatus.PAID:
            raise ValueError(
                f"Cannot verify payment for order {order_id}: "
                f"current status is {order_model.status.value}, expected PAID"
            )

        # Verify payment record exists and matches
        payment_model = await self._payment_repo.get_by_order_id(order_id)
        if payment_model is None:
            raise ValueError(f"No payment record found for order: {order_id}")
        if payment_model.status != PaymentStatus.COMPLETED:
            raise ValueError(
                f"Payment for order {order_id} has status {payment_model.status}, "
                f"expected COMPLETED"
            )
        if payment_model.amount != order_model.total_amount:
            raise ValueError(
                f"Payment amount {payment_model.amount} does not match "
                f"order total {order_model.total_amount}"
            )

        logger.info(
            "Payment verified: order=%s, payment=%s, amount=%s, accountant=%s",
            order_id,
            payment_model.id,
            payment_model.amount,
            accountant_id,
        )
        return self._model_to_domain(order_model)

    async def ship_order(self, order_id: UUID) -> Order:
        """Order Staff ships a paid order (back-office)."""
        order_model = await self._order_repo.get_by_id(order_id)
        if order_model is None:
            raise ValueError(f"Order not found: {order_id}")

        new_status = validate_transition(order_model.status, "ship")
        now = datetime.utcnow()

        # Call shipping API through circuit breaker
        async def call_shipping_api() -> bool:
            # Simulated shipping API call
            return True

        try:
            await shipping_api_cb.call(call_shipping_api)
        except CircuitBreakerOpenError:
            logger.error(
                "Shipping API circuit breaker OPEN for order %s", order_id
            )
            raise

        updated = await self._order_repo.update_with_version_check(
            order_id,
            {
                "status": new_status,
                "shipped_at": now,
                "updated_at": now,
            },
            order_model.version,
        )

        # Publish deferrable work: shipping notification
        await publish_work(
            "shipping_notification",
            {"order_id": str(order_id)},
        )

        logger.info("Order shipped: id=%s", order_id)
        return self._model_to_domain(updated)

    async def close_order(self, order_id: UUID) -> Order:
        """Order Staff closes a completed order (back-office)."""
        order_model = await self._order_repo.get_by_id(order_id)
        if order_model is None:
            raise ValueError(f"Order not found: {order_id}")

        new_status = validate_transition(order_model.status, "close")
        now = datetime.utcnow()

        updated = await self._order_repo.update_with_version_check(
            order_id,
            {
                "status": new_status,
                "closed_at": now,
                "updated_at": now,
            },
            order_model.version,
        )
        logger.info("Order closed: id=%s", order_id)
        return self._model_to_domain(updated)

    async def cancel_order(self, order_id: UUID) -> Order:
        """Cancel an order (allowed from any pre-SHIPPED state).

        On cancellation, stock is restored for each line item so the
        reserved inventory becomes available for other customers.
        """
        order_model = await self._order_repo.get_by_id(order_id)
        if order_model is None:
            raise ValueError(f"Order not found: {order_id}")

        new_status = validate_transition(order_model.status, "cancel")
        now = datetime.utcnow()

        # Restore stock for each line item before updating order status
        line_items = self._order_repo.deserialize_json_list(order_model.line_items)
        for item in line_items:
            product_id = UUID(item["product_id"])
            quantity = int(item["quantity"])
            updated_product = await self._product_repo.increment_stock(
                product_id, quantity
            )
            if updated_product is not None:
                # Invalidate product cache so subsequent reads see restored stock
                await invalidate_product_cache(str(product_id))

        # Invalidate search cache since stock levels changed
        await invalidate_search_cache()

        updated = await self._order_repo.update_with_version_check(
            order_id,
            {
                "status": new_status,
                "cancelled_at": now,
                "updated_at": now,
            },
            order_model.version,
        )
        logger.info("Order cancelled: id=%s", order_id)
        return self._model_to_domain(updated)

    async def get_order(self, order_id: UUID) -> Optional[Order]:
        """Get an order by ID."""
        model = await self._order_repo.get_by_id(order_id)
        if model is None:
            return None
        return self._model_to_domain(model)

    async def list_orders(
        self, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        """List all orders with pagination."""
        models = await self._order_repo.list_all(skip, limit)
        return [self._model_to_domain(m) for m in models]

    def _model_to_domain(self, model) -> Order:
        """Convert ORM model to domain model."""
        return Order(
            id=model.id,
            customer_id=model.customer_id,
            line_items=self._order_repo.deserialize_json_list(model.line_items),
            subtotal=model.subtotal,
            tax_amount=model.tax_amount,
            total_amount=model.total_amount,
            status=model.status,
            invoice_ref=model.invoice_ref,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            accepted_at=model.accepted_at,
            invoiced_at=model.invoiced_at,
            paid_at=model.paid_at,
            shipped_at=model.shipped_at,
            closed_at=model.closed_at,
            cancelled_at=model.cancelled_at,
        )
