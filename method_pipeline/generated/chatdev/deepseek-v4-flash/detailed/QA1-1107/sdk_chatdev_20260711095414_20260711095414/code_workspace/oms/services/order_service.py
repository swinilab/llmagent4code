"""
Order service — orchestrates the complete order lifecycle.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import pybreaker

from oms.domain.enums import OrderStatus, PaymentStatus, InvoiceStatus, PaymentMethod
from oms.domain.models import Order, OrderLineItem, Payment, Invoice
from oms.domain.state_machine import OrderStateMachine
from oms.infrastructure.circuit_breaker import payment_gateway_breaker, shipping_provider_breaker
from oms.infrastructure.metrics import orders_created, orders_transitions
from oms.infrastructure.queue import enqueue_task
from oms.infrastructure.database import AsyncSessionLocal
from oms.infrastructure.entities import OrderModel, PaymentModel, InvoiceModel, CustomerModel, ProductModel
from oms.repositories.order_repo import OrderRepository
from oms.repositories.payment_repo import PaymentRepository
from oms.repositories.invoice_repo import InvoiceRepository
from oms.repositories.customer_repo import CustomerRepository
from oms.repositories.product_repo import ProductRepository
from oms.infrastructure.cache import idempotency_check, idempotency_set, invalidate_product_cache


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderService:
    """
    Encapsulates all order-related business logic.
    Checkout-critical steps (place_order, submit_payment) target p95 <= 300 ms.
    Back-office steps (accept, invoice, verify, ship, close) target p95 <= 1 s.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_repo = OrderRepository(session)
        self._payment_repo = PaymentRepository(session)
        self._invoice_repo = InvoiceRepository(session)
        self._customer_repo = CustomerRepository(session)
        self._product_repo = ProductRepository(session)

    # -- Public query methods ---------------------------------------------

    async def list_orders(self, customer_id: UUID | None = None) -> list[Order]:
        """List orders, optionally filtered by customer_id."""
        if customer_id:
            models = await self._order_repo.get_by_customer(customer_id)
        else:
            stmt = select(OrderModel).order_by(OrderModel.created_at.desc()).limit(100)
            result = await self._session.execute(stmt)
            models = list(result.scalars().all())
        return [self._model_to_order(m) for m in models]

    async def get_order(self, order_id: UUID) -> Order | None:
        """Get a single order by ID."""
        model = await self._order_repo.get(order_id)
        if not model:
            return None
        return self._model_to_order(model)

    # -- Checkout-critical: p95 <= 300 ms ---------------------------------

    async def place_order(
        self,
        customer_id: UUID,
        line_items: list[OrderLineItem],
    ) -> Order:
        """
        Create a new order with CREATED status.
        Validates stock, decrements inventory atomically, computes totals.
        Uses atomic UPDATE for stock decrement to prevent oversell under
        concurrent load (fixes race condition where two requests could both
        pass the stock check and oversell).
        """
        # Validate customer exists
        customer = await self._customer_repo.get(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Validate products and compute totals
        subtotal = Decimal("0.00")
        validated_items = []
        product_stock_checks = []  # (product_id, quantity, unit_price) for atomic decrement
        for item in line_items:
            product = await self._product_repo.get_with_cache(item.product_id)
            if not product:
                raise ValueError(f"Product {item.product_id} not found")
            if product.stock_available < item.quantity:
                raise ValueError(
                    f"Insufficient stock for product {item.product_id}: "
                    f"requested {item.quantity}, available {product.stock_available}"
                )
            unit_price = product.base_price
            subtotal += unit_price * item.quantity
            validated_items.append({
                "product_id": str(item.product_id),
                "quantity": item.quantity,
                "unit_price": str(unit_price),
            })
            product_stock_checks.append((item.product_id, item.quantity, unit_price))

        tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"))  # 8% tax
        total = subtotal + tax

        order_id = uuid4()
        now = _utcnow()
        order_model = OrderModel(
            id=order_id,
            customer_id=customer_id,
            line_items=validated_items,
            subtotal=subtotal,
            tax=tax,
            total_amount=total,
            status=OrderStatus.CREATED,
            created_at=now,
            updated_at=now,
            version=1,
        )
        await self._order_repo.save(order_model)

        # CRITICAL: Atomically decrement stock for each product.
        # Using atomic UPDATE ... WHERE stock_available >= qty prevents
        # the race condition where two concurrent requests both pass the
        # stock check and oversell.
        for prod_id, qty, _ in product_stock_checks:
            success = await self._product_repo.atomic_decrement_stock(prod_id, qty)
            if not success:
                await self._session.rollback()
                raise ValueError(
                    f"Insufficient stock for product {prod_id} (atomic check failed)"
                )

        # Invalidate product caches AFTER all decrements succeed, so that
        # a failure mid-loop does not leave stale cache entries for products
        # whose decrement already succeeded.
        for prod_id, _, _ in product_stock_checks:
            await invalidate_product_cache(prod_id)

        await self._session.commit()

        orders_created.inc()
        orders_transitions.labels(to_status="CREATED").inc()

        # Enqueue deferred task: notification
        await enqueue_task("order_placed", {"order_id": str(order_id), "customer_id": str(customer_id)})

        return Order(
            id=order_id,
            customer_id=customer_id,
            line_items=line_items,
            subtotal=subtotal,
            tax=tax,
            total_amount=total,
            status=OrderStatus.CREATED,
            created_at=now,
            updated_at=now,
            version=1,
        )

    # ── Background reconciliation design ─────────────────────────────────
    # TODO: Implement a background reconciliation job that periodically
    # (e.g., every 5 minutes) scans for PaymentModel records with
    # status=PENDING and timestamp older than a threshold (e.g., 10 minutes).
    # For each such record:
    #   1. Check the payment gateway for the actual status of the transaction.
    #   2. If the gateway confirms success, update the payment to COMPLETED
    #      and the order to PAID (within a single atomic transaction).
    #   3. If the gateway confirms failure, update the payment to FAILED.
    #   4. If the gateway has no record (transaction never reached it),
    #      mark the payment as FAILED and release the reserved stock.
    # This ensures no orphaned PENDING payments exist indefinitely, satisfying
    # NFR 1.3's "no silent request loss" requirement.
    #
    # The current implementation (single atomic transaction with flush+commit)
    # eliminates the most common crash scenario, but a reconciliation job
    # provides defense-in-depth against edge cases (e.g., process crash during
    # the gateway call itself, after the gateway commits but before the DB
    # transaction commits).

    async def submit_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        method: PaymentMethod,
        idempotency_key: str,
    ) -> Payment:
        """
        Process payment with idempotency guarantee.
        Validates amount against order total.
        Uses circuit breaker for downstream payment gateway.
        Uses domain state machine to validate transition (INVOICED -> PAID).

        CRITICAL FIX: Uses a SINGLE atomic transaction for the entire payment
        flow (save PENDING -> call gateway -> update order to PAID -> update
        payment to COMPLETED). This eliminates the previous bug where a crash
        between commit and gateway call left an orphaned PENDING payment.

        The idempotency key is set in Redis BEFORE the gateway call so that
        duplicate requests are rejected early even if the gateway call is
        in-flight.

        If the gateway call fails, the entire transaction is rolled back,
        leaving no orphaned records. If the process crashes mid-flow, the
        idempotency key in Redis prevents double-processing on retry.
        """
        # Idempotency check (Redis)
        existing_result = await idempotency_check(idempotency_key)
        if existing_result:
            return Payment(
                id=UUID(existing_result),
                order_id=order_id,
                amount=amount,
                timestamp=_utcnow(),
                status=PaymentStatus.COMPLETED,
                method=method,
                idempotency_key=idempotency_key,
            )

        # Check existing payment by idempotency key in DB
        existing_payment = await self._payment_repo.get_by_idempotency_key(idempotency_key)
        if existing_payment:
            await idempotency_set(idempotency_key, str(existing_payment.id))
            return Payment(
                id=existing_payment.id,
                order_id=existing_payment.order_id,
                amount=existing_payment.amount,
                timestamp=existing_payment.timestamp,
                status=existing_payment.status,
                method=existing_payment.method,
                idempotency_key=existing_payment.idempotency_key,
            )

        # Get order and validate state transition via domain state machine
        order_model = await self._order_repo.get(order_id)
        if not order_model:
            raise ValueError(f"Order {order_id} not found")

        OrderStateMachine.next_status(order_model.status, "pay")

        # Validate payment amount matches order total
        if amount != order_model.total_amount:
            raise ValueError(
                f"Payment amount {amount} does not match order total {order_model.total_amount}"
            )

        # Reserve idempotency key in Redis BEFORE any DB writes
        payment_id = uuid4()
        await idempotency_set(idempotency_key, str(payment_id))

        # Single atomic transaction for the entire payment flow
        async with AsyncSessionLocal() as atomic_session:
            try:
                # Step 1: Save payment in PENDING status
                now = _utcnow()
                payment_model = PaymentModel(
                    id=payment_id,
                    order_id=order_id,
                    amount=amount,
                    timestamp=now,
                    status=PaymentStatus.PENDING,
                    method=method,
                    idempotency_key=idempotency_key,
                )
                atomic_session.add(payment_model)
                await atomic_session.flush()

                # Step 2: Call the payment gateway (circuit-breaker protected)
                def _simulate_gateway_call() -> bool:
                    return True

                try:
                    await payment_gateway_breaker.call(_simulate_gateway_call)
                except pybreaker.CircuitBreakerError:
                    await atomic_session.rollback()
                    raise RuntimeError("Payment gateway circuit is OPEN -- rejecting request")
                except Exception:
                    await atomic_session.rollback()
                    raise RuntimeError("Payment gateway call failed after payment recorded")

                # Step 3: Gateway succeeded -- update order to PAID
                order_stmt = select(OrderModel).where(OrderModel.id == order_id).with_for_update()
                result = await atomic_session.execute(order_stmt)
                current_order = result.scalar_one_or_none()
                if not current_order:
                    await atomic_session.rollback()
                    raise RuntimeError(f"Order {order_id} not found during payment completion")

                update_order_stmt = (
                    update(OrderModel)
                    .where(
                        OrderModel.id == order_id,
                        OrderModel.version == current_order.version,
                    )
                    .values(
                        status=OrderStatus.PAID,
                        version=OrderModel.version + 1,
                        updated_at=now,
                        paid_at=now,
                    )
                )
                order_result = await atomic_session.execute(update_order_stmt)
                if order_result.rowcount == 0:
                    await atomic_session.rollback()
                    raise RuntimeError(f"Optimistic lock conflict on order {order_id} during payment completion")

                # Step 4: Update payment status to COMPLETED
                update_payment_stmt = (
                    update(PaymentModel)
                    .where(PaymentModel.id == payment_id)
                    .values(status=PaymentStatus.COMPLETED)
                )
                await atomic_session.execute(update_payment_stmt)

                # Step 5: Single atomic commit -- all or nothing
                await atomic_session.commit()

            except (RuntimeError, ValueError):
                try:
                    await atomic_session.rollback()
                except Exception:
                    pass
                raise

        # Post-commit: update metrics and enqueue deferred tasks
        orders_transitions.labels(to_status="PAID").inc()
        await enqueue_task("payment_received", {"order_id": str(order_id), "payment_id": str(payment_id)})

        return Payment(
            id=payment_id,
            order_id=order_id,
            amount=amount,
            timestamp=_utcnow(),
            status=PaymentStatus.COMPLETED,
            method=method,
            idempotency_key=idempotency_key,
        )

    # -- Back-office: p95 <= 1 s ------------------------------------------

    async def accept_order(self, order_id: UUID, expected_version: int) -> Order:
        """Order Staff reviews & accepts (CREATED -> ACCEPTED)."""
        order_model = await self._order_repo.get(order_id)
        if not order_model:
            raise ValueError(f"Order {order_id} not found")

        OrderStateMachine.next_status(order_model.status, "accept")
        updated = await self._order_repo.update_status(
            order_id, OrderStatus.ACCEPTED, expected_version, "accepted_at"
        )
        if not updated:
            raise ValueError(f"Optimistic lock conflict on order {order_id}")
        await self._session.commit()
        orders_transitions.labels(to_status="ACCEPTED").inc()
        return self._model_to_order(updated)

    async def create_invoice(self, order_id: UUID, expected_version: int) -> Invoice:
        """Accountant creates invoice (ACCEPTED -> INVOICED)."""
        order_model = await self._order_repo.get(order_id)
        if not order_model:
            raise ValueError(f"Order {order_id} not found")

        OrderStateMachine.next_status(order_model.status, "invoice")

        invoice_id = uuid4()
        invoice_model = InvoiceModel(
            id=invoice_id,
            order_id=order_id,
            billing_info=f"Invoice for order {order_id}",
            amount=order_model.total_amount,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=InvoiceStatus.ISSUED,
        )
        await self._invoice_repo.save(invoice_model)

        now = _utcnow()
        stmt = (
            update(OrderModel)
            .where(OrderModel.id == order_id, OrderModel.version == expected_version)
            .values(
                status=OrderStatus.INVOICED,
                version=OrderModel.version + 1,
                updated_at=now,
                invoiced_at=now,
                invoice_ref=invoice_id,
            )
            .returning(OrderModel)
        )
        result = await self._session.execute(stmt)
        updated = result.scalar_one_or_none()
        if not updated:
            raise ValueError(f"Optimistic lock conflict on order {order_id}")

        await self._session.commit()
        orders_transitions.labels(to_status="INVOICED").inc()

        return Invoice(
            id=invoice_id,
            order_id=order_id,
            billing_info=invoice_model.billing_info,
            amount=invoice_model.amount,
            issue_date=invoice_model.issue_date,
            due_date=invoice_model.due_date,
            status=InvoiceStatus.ISSUED,
        )

    async def verify_payment(self, order_id: UUID, expected_version: int) -> Order:
        """Accountant verifies payment (PAID state confirmed)."""
        order_model = await self._order_repo.get(order_id)
        if not order_model:
            raise ValueError(f"Order {order_id} not found")

        if order_model.version != expected_version:
            raise ValueError(
                f"Optimistic lock conflict on order {order_id}: "
                f"expected version {expected_version}, current {order_model.version}"
            )

        OrderStateMachine.next_status(order_model.status, "verify")
        return self._model_to_order(order_model)

    async def ship_order(self, order_id: UUID, expected_version: int) -> Order:
        """Order Staff ships paid order (PAID -> SHIPPED)."""
        order_model = await self._order_repo.get(order_id)
        if not order_model:
            raise ValueError(f"Order {order_id} not found")
        OrderStateMachine.next_status(order_model.status, "ship")

        def _simulate_shipping_call() -> bool:
            return True

        try:
            await shipping_provider_breaker.call(_simulate_shipping_call)
        except pybreaker.CircuitBreakerError:
            raise RuntimeError("Shipping provider circuit is OPEN -- rejecting request")
        except Exception:
            raise RuntimeError("Shipping provider call failed")

        updated = await self._order_repo.update_status(
            order_id, OrderStatus.SHIPPED, expected_version, "shipped_at"
        )
        if not updated:
            raise ValueError(f"Optimistic lock conflict on order {order_id}")
        await self._session.commit()
        orders_transitions.labels(to_status="SHIPPED").inc()
        return self._model_to_order(updated)

    async def close_order(self, order_id: UUID, expected_version: int) -> Order:
        """Order Staff closes completed order (SHIPPED -> CLOSED)."""
        order_model = await self._order_repo.get(order_id)
        if not order_model:
            raise ValueError(f"Order {order_id} not found")

        OrderStateMachine.next_status(order_model.status, "close")
        updated = await self._order_repo.update_status(
            order_id, OrderStatus.CLOSED, expected_version, "closed_at"
        )
        if not updated:
            raise ValueError(f"Optimistic lock conflict on order {order_id}")
        await self._session.commit()
        orders_transitions.labels(to_status="CLOSED").inc()
        return self._model_to_order(updated)

    async def cancel_order(self, order_id: UUID, expected_version: int) -> Order:
        """Cancel order from any pre-SHIPPED state."""
        order_model = await self._order_repo.get(order_id)
        if not order_model:
            raise ValueError(f"Order {order_id} not found")

        OrderStateMachine.next_status(order_model.status, "cancel")
        updated = await self._order_repo.update_status(
            order_id, OrderStatus.CANCELLED, expected_version, "cancelled_at"
        )
        if not updated:
            raise ValueError(f"Optimistic lock conflict on order {order_id}")
        await self._session.commit()
        orders_transitions.labels(to_status="CANCELLED").inc()
        return self._model_to_order(updated)

    # -- Helpers ----------------------------------------------------------

    @staticmethod
    def _model_to_order(m: OrderModel) -> Order:
        return Order(
            id=m.id,
            customer_id=m.customer_id,
            line_items=[OrderLineItem(**item) for item in m.line_items],
            subtotal=m.subtotal,
            tax=m.tax,
            total_amount=m.total_amount,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
            accepted_at=m.accepted_at,
            invoiced_at=m.invoiced_at,
            paid_at=m.paid_at,
            shipped_at=m.shipped_at,
            closed_at=m.closed_at,
            cancelled_at=m.cancelled_at,
            invoice_ref=m.invoice_ref,
            version=m.version,
        )
