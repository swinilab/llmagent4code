# Order service -- core business logic for order lifecycle.
#
# Each method manages its own transaction boundary via the injected session.
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from oms.config import settings
from oms.domain.enums import OrderStatus, PaymentStatus, UserRole
from oms.domain.models import LineItem, Order
from oms.domain.order_state import OrderStateMachine
from oms.infrastructure.cache import cache
from oms.infrastructure.circuit_breaker import get_circuit_breaker
from oms.infrastructure.message_queue import mq
from oms.infrastructure.state_recovery import write_outbox
from oms.repositories.orm_models import (
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
    PaymentRepository,
    ProductRepository,
)

logger = logging.getLogger(__name__)


class OrderService:
    """Order lifecycle orchestration."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.product_repo = ProductRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.invoice_repo = InvoiceRepository(session)

    async def create_order(self, customer_id: str, line_items: list[dict]) -> Order:
        """Step 1: Customer places order. (Checkout-critical, Core)"""
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        items = []
        total = Decimal("0.00")
        for item in line_items:
            # Use pessimistic lock to prevent TOCTOU race on stock
            product = await self.product_repo.get_by_id_with_lock(item["product_id"])
            if not product:
                raise ValueError(f"Product {item['product_id']} not found")
            if product.stock_available < item["quantity"]:
                raise ValueError(f"Insufficient stock for product {product.name}")

            # Decrement stock (critical business logic - was missing!)
            product.stock_available -= item["quantity"]
            product.last_modified = datetime.now(timezone.utc)

            unit_price = product.base_price
            items.append(
                LineItem(
                    product_id=product.id,
                    product_name=product.name,
                    quantity=item["quantity"],
                    unit_price=unit_price,
                    currency=product.currency,
                )
            )
            total += unit_price * item["quantity"]

        order_dict = {
            "customer_id": customer_id,
            "line_items": json.dumps([it.model_dump(mode="json") for it in items]),
            "total_amount": total,
            "currency": "USD",
            "status": OrderStatus.CREATED.value,
        }
        orm = await self.order_repo.create(order_dict)

        # Write outbox entry for event
        await write_outbox(
            self.session,
            orm.id,
            "order.created",
            {"order_id": orm.id, "customer_id": customer_id, "total": str(total)},
        )

        # Invalidate cache
        await cache.delete(f"order:{orm.id}")
        # Invalidate product caches since stock changed
        for item in line_items:
            await cache.delete(f"product:{item['product_id']}")

        return Order(
            id=orm.id,
            customer_id=orm.customer_id,
            line_items=items,
            total_amount=total,
            currency="USD",
            status=OrderStatus.CREATED,
            version=orm.version,
            created_at=orm.created_at,
        )

    async def accept_order(self, order_id: str, version: int, role: str = UserRole.ORDER_STAFF.value) -> Order:
        """Step 2: Order Staff reviews & accepts. (Relaxed back-office, Core)"""
        if role not in (UserRole.ORDER_STAFF.value, UserRole.ACCOUNTANT.value):
            raise ValueError(f"Role '{role}' is not authorized to accept orders. Requires ORDER_STAFF or ACCOUNTANT.")
        orm = await self.order_repo.get_by_id(order_id)
        if not orm:
            raise ValueError(f"Order {order_id} not found")

        new_status = OrderStateMachine.transition(OrderStatus(orm.status), "accept")
        updated = await self.order_repo.update_status(
            order_id, new_status.value, version, "accepted_at"
        )
        if not updated:
            raise ValueError("Optimistic lock conflict -- order was modified concurrently")

        await write_outbox(
            self.session, order_id, "order.accepted", {"order_id": order_id}
        )
        await cache.delete(f"order:{order_id}")

        return await self._load_order(order_id)

    async def invoice_order(self, order_id: str, version: int, billing_address: str, role: str = UserRole.ACCOUNTANT.value) -> dict:
        """Step 3: Accountant creates invoice. (Relaxed back-office, Core)"""
        if role != UserRole.ACCOUNTANT.value:
            raise ValueError(f"Role '{role}' is not authorized to invoice orders. Requires ACCOUNTANT.")
        orm = await self.order_repo.get_by_id(order_id)
        if not orm:
            raise ValueError(f"Order {order_id} not found")

        new_status = OrderStateMachine.transition(OrderStatus(orm.status), "invoice")
        updated = await self.order_repo.update_status(
            order_id, new_status.value, version, "invoiced_at"
        )
        if not updated:
            raise ValueError("Optimistic lock conflict")

        # Create invoice
        invoice_dict = {
            "order_id": order_id,
            "customer_id": orm.customer_id,
            "billing_address": billing_address,
            "total_amount": orm.total_amount,
            "currency": orm.currency,
            "status": "ISSUED",
            "issue_date": datetime.now(timezone.utc),
            "due_date": datetime.now(timezone.utc) + timedelta(days=30),
        }

        inv_orm = await self.invoice_repo.create(invoice_dict)

        # Update order with invoice ref
        await self.session.execute(
            text("UPDATE orders SET invoice_ref = :inv_id WHERE id = :order_id"),
            {"inv_id": inv_orm.id, "order_id": order_id},
        )

        await write_outbox(
            self.session, order_id, "order.invoiced",
            {"order_id": order_id, "invoice_id": inv_orm.id},
        )
        await cache.delete(f"order:{order_id}")

        return {"invoice_id": inv_orm.id, "order_id": order_id, "total": str(orm.total_amount)}

    async def pay_order(self, order_id: str, amount: Decimal, method: str, idempotency_key: str) -> dict:
        """Step 4: Customer pays invoice. (Checkout-critical, Core)

        Uses pessimistic locking (SELECT ... FOR UPDATE) to serialize concurrent
        payment attempts and eliminate the TOCTOU race between idempotency check
        and order status update. The idempotency key has a UNIQUE constraint in
        the database as a secondary safeguard.
        """
        # Acquire pessimistic lock on the order row to serialize concurrent payments
        orm = await self.order_repo.get_by_id_with_lock(order_id)
        if not orm:
            raise ValueError(f"Order {order_id} not found")
        if amount != orm.total_amount:
            raise ValueError(
                f"Payment amount {amount} does not match order total {orm.total_amount}"
            )

        # Re-check idempotency INSIDE the lock — no race window possible
        existing = await self.payment_repo.get_by_idempotency_key(idempotency_key)
        if existing:
            return {
                "payment_id": existing.id,
                "order_id": order_id,
                "status": existing.status,
                "idempotent": True,
            }

        new_status = OrderStateMachine.transition(OrderStatus(orm.status), "pay")
        updated = await self.order_repo.update_status(
            order_id, new_status.value, orm.version, "paid_at"
        )
        if not updated:
            # Under FOR UPDATE lock this should not happen, but handle gracefully
            # by re-checking idempotency (defensive)
            existing = await self.payment_repo.get_by_idempotency_key(idempotency_key)
            if existing:
                return {
                    "payment_id": existing.id,
                    "order_id": order_id,
                    "status": existing.status,
                    "idempotent": True,
                }
            raise ValueError("Optimistic lock conflict")

        payment_dict = {
            "order_id": order_id,
            "amount": amount,
            "currency": orm.currency,
            "method": method,
            "status": PaymentStatus.COMPLETED.value,
            "idempotency_key": idempotency_key,
            "completed_at": datetime.now(timezone.utc),
        }
        pay_orm = await self.payment_repo.create(payment_dict)

        # Update invoice status
        inv = await self.invoice_repo.get_by_order_id(order_id)
        if inv:
            await self.invoice_repo.update_status(inv.id, "PAID")

        await write_outbox(
            self.session, order_id, "order.paid",
            {"order_id": order_id, "payment_id": pay_orm.id},
        )
        await cache.delete(f"order:{order_id}")

        return {"payment_id": pay_orm.id, "order_id": order_id, "status": "COMPLETED"}

    async def verify_payment(self, order_id: str) -> dict:
        """Step 5: Accountant verifies payment. (Relaxed back-office, Core)"""
        payment = await self.payment_repo.get_by_order_id(order_id)
        if not payment:
            raise ValueError(f"No payment found for order {order_id}")
        return {
            "payment_id": payment.id,
            "order_id": order_id,
            "status": payment.status,
            "amount": str(payment.amount),
            "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
        }

    async def ship_order(self, order_id: str, version: int, role: str = UserRole.ORDER_STAFF.value) -> Order:
        """Step 6: Order Staff ships paid order. (Relaxed back-office, Core)"""
        if role != UserRole.ORDER_STAFF.value:
            raise ValueError(f"Role '{role}' is not authorized to ship orders. Requires ORDER_STAFF.")
        orm = await self.order_repo.get_by_id(order_id)
        if not orm:
            raise ValueError(f"Order {order_id} not found")

        new_status = OrderStateMachine.transition(OrderStatus(orm.status), "ship")
        updated = await self.order_repo.update_status(
            order_id, new_status.value, version, "shipped_at"
        )
        if not updated:
            raise ValueError("Optimistic lock conflict")

        await write_outbox(
            self.session, order_id, "order.shipped", {"order_id": order_id}
        )
        await cache.delete(f"order:{order_id}")

        return await self._load_order(order_id)

    async def close_order(self, order_id: str, version: int, role: str = UserRole.ORDER_STAFF.value) -> Order:
        """Step 7: Order Staff closes completed order. (Relaxed back-office, Core)"""
        if role != UserRole.ORDER_STAFF.value:
            raise ValueError(f"Role '{role}' is not authorized to close orders. Requires ORDER_STAFF.")
        orm = await self.order_repo.get_by_id(order_id)
        if not orm:
            raise ValueError(f"Order {order_id} not found")

        new_status = OrderStateMachine.transition(OrderStatus(orm.status), "close")
        updated = await self.order_repo.update_status(
            order_id, new_status.value, version, "closed_at"
        )
        if not updated:
            raise ValueError("Optimistic lock conflict")

        await write_outbox(
            self.session, order_id, "order.closed", {"order_id": order_id}
        )
        await cache.delete(f"order:{order_id}")

        return await self._load_order(order_id)

    async def cancel_order(self, order_id: str, version: int) -> Order:
        """Cancel an order (terminal exception state). Restores stock."""
        orm = await self.order_repo.get_by_id(order_id)
        if not orm:
            raise ValueError(f"Order {order_id} not found")

        new_status = OrderStateMachine.transition(OrderStatus(orm.status), "cancel")
        updated = await self.order_repo.update_status(
            order_id, new_status.value, version, "cancelled_at"
        )
        if not updated:
            raise ValueError("Optimistic lock conflict")

        # Restore stock for each product in the cancelled order
        items_data = json.loads(orm.line_items) if isinstance(orm.line_items, str) else orm.line_items
        for item in items_data:
            product = await self.product_repo.get_by_id_with_lock(item["product_id"])
            if product:
                product.stock_available += item["quantity"]
                product.last_modified = datetime.now(timezone.utc)
                await cache.delete(f"product:{item['product_id']}")

        await write_outbox(
            self.session, order_id, "order.cancelled", {"order_id": order_id}
        )
        await cache.delete(f"order:{order_id}")

        return await self._load_order(order_id)

    async def get_order(self, order_id: str) -> Order:
        """Get order by ID (with cache-aside)."""
        cached = await cache.get(f"order:{order_id}")
        if cached:
            return Order(**cached)

        orm = await self.order_repo.get_by_id(order_id)
        if not orm:
            raise ValueError(f"Order {order_id} not found")

        order = await self._load_order(order_id)
        await cache.set(f"order:{order_id}", order.model_dump(mode="json"), ttl_seconds=settings.cache_ttl_orders)
        return order

    async def list_orders(self, customer_id: Optional[str] = None) -> list[Order]:
        """List orders, optionally filtered by customer."""
        if customer_id:
            orms = await self.order_repo.list_by_customer(customer_id)
        else:
            orms = await self.order_repo.list_all()

        result = []
        for orm in orms:
            result.append(await self._load_order_from_orm(orm))
        return result

    async def _load_order(self, order_id: str) -> Order:
        orm = await self.order_repo.get_by_id(order_id)
        return await self._load_order_from_orm(orm)

    async def _load_order_from_orm(self, orm) -> Order:
        items_data = json.loads(orm.line_items) if isinstance(orm.line_items, str) else orm.line_items
        items = [LineItem(**it) for it in items_data]
        return Order(
            id=orm.id,
            customer_id=orm.customer_id,
            line_items=items,
            total_amount=orm.total_amount,
            currency=orm.currency,
            status=OrderStatus(orm.status),
            invoice_ref=orm.invoice_ref,
            version=orm.version,
            created_at=orm.created_at,
            accepted_at=orm.accepted_at,
            invoiced_at=orm.invoiced_at,
            paid_at=orm.paid_at,
            shipped_at=orm.shipped_at,
            closed_at=orm.closed_at,
            cancelled_at=orm.cancelled_at,
        )


class ProductService:
    """Product catalog service with cache-aside."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductRepository(session)

    async def search_products(self, query: str) -> list[dict]:
        """Search products (latency-sensitive, p95 <= 150ms)."""
        cache_key = f"search:{query.lower()}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        orms = await self.repo.search(query)
        result = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "base_price": str(p.base_price),
                "currency": p.currency,
                "stock_available": p.stock_available,
            }
            for p in orms
        ]
        await cache.set(cache_key, result, ttl_seconds=settings.cache_ttl_products)
        return result

    async def get_product(self, product_id: str) -> dict:
        """Get product by ID with cache-aside."""
        cache_key = f"product:{product_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        orm = await self.repo.get_by_id(product_id)
        if not orm:
            raise ValueError(f"Product {product_id} not found")

        result = {
            "id": orm.id,
            "name": orm.name,
            "description": orm.description,
            "base_price": str(orm.base_price),
            "currency": orm.currency,
            "stock_available": orm.stock_available,
        }
        await cache.set(cache_key, result, ttl_seconds=settings.cache_ttl_products)
        return result

    async def list_products(self) -> list[dict]:
        orms = await self.repo.list_all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "base_price": str(p.base_price),
                "currency": p.currency,
                "stock_available": p.stock_available,
            }
            for p in orms
        ]


class RecommendationService:
    """Non-essential service: personalized recommendations (NFR 2.1).

    Protected by circuit breaker -- falls back to cached/generic recommendations.
    Fallback is passed as a parameter to call() to avoid race conditions on
    shared instance state.

    Includes a timeout on the downstream call to prevent hanging requests
    from keeping the circuit closed.
    """

    def __init__(self):
        self.cb = get_circuit_breaker("recommendations")

    async def get_recommendations(self, customer_id: str) -> list[dict]:
        """Get personalized recommendations with circuit breaker protection."""

        async def _fetch():
            """Simulate external recommendation API call with timeout.

            In production, this would call an external ML service via HTTP.
            The asyncio.timeout ensures the circuit breaker opens if the
            downstream service hangs (NFR 2.1).
            """
            import asyncio
            try:
                async with asyncio.timeout(2.0):  # 2-second timeout
                    # Simulate external API call
                    # In production: return await httpx.AsyncClient().get(...)
                    await asyncio.sleep(0.05)  # Simulate network latency
                    return [
                        {"product_id": "rec-1", "name": "Recommended Item 1", "score": 0.95},
                        {"product_id": "rec-2", "name": "Recommended Item 2", "score": 0.87},
                    ]
            except asyncio.TimeoutError:
                raise TimeoutError("Recommendation service timed out")

        async def _fallback():
            return [
                {"product_id": "generic-1", "name": "Popular Item 1", "score": 0.5},
                {"product_id": "generic-2", "name": "Popular Item 2", "score": 0.5},
            ]

        # Pass fallback as parameter to avoid race condition on shared cb._fallback
        return await self.cb.call(_fetch, fallback=_fallback)
