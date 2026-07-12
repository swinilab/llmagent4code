"""
OrderService — orchestrates the order lifecycle: create → accept → (fulfill) → ship → close.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oms_backend.models.orm_models import Customer, LineItem, Order, Product
from oms_backend.repositories.entities import (
    CustomerRepository,
    LineItemRepository,
    OrderRepository,
    ProductRepository,
)
from oms_backend.services.utils import audit_log
from oms_backend.schemas.domain import OrderStatus


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.line_item_repo = LineItemRepository(session)
        self.product_repo = ProductRepository(session)
        self.customer_repo = CustomerRepository(session)

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, data: OrderCreate, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Order:
        """
        Place a new order for a customer.
        1. Snapshot product prices
        2. Calculate subtotals and tax
        3. Persist order + line items
        4. Audit log
        """
        # Verify customer exists
        customer = await self.customer_repo.get_active(data.customer_id)
        if not customer:
            raise ValueError(f"Customer {data.customer_id} not found")

        # Validate product IDs and snapshot prices
        product_ids = [item.product_id for item in data.items]
        products = {p.id: p for p in await self.product_repo.get_bulk(product_ids)}

        for item in data.items:
            if item.product_id not in products:
                raise ValueError(f"Product {item.product_id} not found")
            if not products[item.product_id].is_active:
                raise ValueError(f"Product {products[item.product_id].sku} is not active")

        # Generate code
        code = await self.order_repo.next_code()

        # Build line item records (price snapshot + line total)
        line_item_records: list[dict[str, Any]] = []
        subtotal = Decimal("0")
        tax_amount = Decimal("0")

        for item in data.items:
            product = products[item.product_id]
            gross = product.base_price * Decimal(item.quantity)
            tax = gross * item.tax_rate
            line_total = (gross + tax).quantize(Decimal("0.0001"))
            subtotal += gross.quantize(Decimal("0.0001"))
            tax_amount += tax.quantize(Decimal("0.0001"))
            line_item_records.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": product.base_price,
                "tax_rate": item.tax_rate,
                "line_total": line_total,
            })

        total_amount = (subtotal + tax_amount).quantize(Decimal("0.0001"))

        # Persist order
        order = await self.order_repo.create(
            code=code,
            customer_id=data.customer_id,
            status=OrderStatus.PENDING.value,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency="USD",
            notes=data.notes,
            ship_address=data.ship_address,
            ship_city=data.ship_city,
            ship_state=data.ship_state,
            ship_postal=data.ship_postal,
            ship_country=data.ship_country,
            created_by=actor_id,
        )

        # Persist line items
        await self.line_item_repo.create_bulk(order.id, line_item_records)

        # Reserve stock atomically — fails if insufficient quantity remains
        reserved_items: list[tuple[uuid.UUID, int]] = []
        for item in data.items:
            reserved = await self.product_repo.reserve_stock(item.product_id, item.quantity)
            if not reserved:
                # Rollback previously reserved items in this order
                for prev_product_id, prev_qty in reserved_items:
                    await self.product_repo.restore_stock(prev_product_id, prev_qty)
                raise ValueError(f"Insufficient stock for {products[item.product_id].sku}")
            reserved_items.append((item.product_id, item.quantity))

        await audit_log(self.session, "order", order.id, "created",
                        actor_id=actor_id,
                        payload={"code": code, "total": str(total_amount)},
                        ip_address=ip_address)

        return await self.order_repo.get_with_items(order.id)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get(self, id: uuid.UUID) -> Order | None:
        return await self.order_repo.get_with_items(id)

    async def get_by_code(self, code: str) -> Order | None:
        return await self.order_repo.get_by_code(code)

    async def list_for_customer(self, customer_id: uuid.UUID, page: int = 1, page_size: int = 20) -> tuple[list[Order], int]:
        return await self.order_repo.list_by_customer(customer_id, page, page_size)

    async def list_by_status(self, status: str, page: int = 1, page_size: int = 20) -> tuple[list[Order], int]:
        return await self.order_repo.list_by_status(status, page, page_size)

    async def list_all(self, page: int = 1, page_size: int = 20) -> tuple[list[Order], int]:
        return await self.order_repo.list_all(page=page, page_size=page_size, order_by="created_at", descending=True)

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(self, id: uuid.UUID, data: OrderUpdate, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Order | None:
        order = await self.order_repo.get_active(id)
        if not order:
            return None
        if order.status != OrderStatus.PENDING.value:
            raise ValueError(f"Cannot update order in {order.status} status")

        update_data: dict[str, Any] = {}
        if data.notes is not None:
            update_data["notes"] = data.notes
        if data.ship_address is not None:
            update_data["ship_address"] = data.ship_address
        if data.ship_city is not None:
            update_data["ship_city"] = data.ship_city
        if data.ship_state is not None:
            update_data["ship_state"] = data.ship_state
        if data.ship_postal is not None:
            update_data["ship_postal"] = data.ship_postal
        if data.ship_country is not None:
            update_data["ship_country"] = data.ship_country

        if update_data:
            await self.order_repo.update(id, **update_data)
            await audit_log(self.session, "order", id, "updated", actor_id=actor_id, payload=update_data, ip_address=ip_address)

        return await self.order_repo.get_with_items(id)

    # ── Lifecycle: Accept ──────────────────────────────────────────────────────

    async def accept(self, id: uuid.UUID, data: OrderAccept | None = None, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Order | None:
        """
        Order Staff approves a pending order.
        Only pending orders can be accepted.
        """
        order = await self.order_repo.get_with_items(id)
        if not order:
            return None
        if order.status != OrderStatus.PENDING.value:
            raise ValueError(f"Order {order.code} is {order.status}; only pending orders can be accepted")

        update_data: dict[str, Any] = {"notes": order.notes}
        if data and data.notes:
            update_data["notes"] = (order.notes or "") + f"\n[accept] {data.notes}"

        updated = await self.order_repo.update_status(id, OrderStatus.ACCEPTED.value)
        if updated:
            await self.order_repo.update(id, accepted_by=actor_id, notes=update_data["notes"])
            await audit_log(self.session, "order", id, "accepted", actor_id=actor_id, ip_address=ip_address)
        return await self.order_repo.get_with_items(id)

    # ── Lifecycle: Ship ───────────────────────────────────────────────────────

    async def ship(self, id: uuid.UUID, data: OrderShip | None = None, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Order | None:
        """
        Order Staff ships a paid order.
        """
        order = await self.order_repo.get_with_items(id)
        if not order:
            return None
        if order.status != OrderStatus.PAID.value:
            raise ValueError(f"Order {order.code} is {order.status}; only paid orders can be shipped")

        update_data: dict[str, Any] = {}
        if data and data.tracking_number:
            update_data["tracking_number"] = data.tracking_number

        await self.order_repo.update(id, **update_data)
        updated = await self.order_repo.update_status(id, OrderStatus.SHIPPED.value)
        if updated:
            await audit_log(self.session, "order", id, "shipped", actor_id=actor_id, payload={"tracking": data.tracking_number if data else None}, ip_address=ip_address)
        return await self.order_repo.get_with_items(id)

    # ── Lifecycle: Close ──────────────────────────────────────────────────────

    async def close(self, id: uuid.UUID, data: OrderClose | None = None, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Order | None:
        """
        Order Staff closes a delivered order.
        """
        order = await self.order_repo.get_with_items(id)
        if not order:
            return None
        if order.status not in (OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value):
            raise ValueError(f"Order {order.code} is {order.status}; must be shipped or delivered to close")

        update_data: dict[str, Any] = {}
        if data and data.notes:
            update_data["notes"] = (order.notes or "") + f"\n[close] {data.notes}"

        if update_data:
            await self.order_repo.update(id, **update_data)

        updated = await self.order_repo.update_status(id, OrderStatus.CLOSED.value)
        if updated:
            await audit_log(self.session, "order", id, "closed", actor_id=actor_id, ip_address=ip_address)
        return await self.order_repo.get_with_items(id)

    # ── Lifecycle: Cancel ─────────────────────────────────────────────────────

    async def cancel(self, id: uuid.UUID, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Order | None:
        """
        Cancel a pending or accepted order and restore stock.
        """
        order = await self.order_repo.get_with_items(id)
        if not order:
            return None
        if order.status not in (OrderStatus.PENDING.value, OrderStatus.ACCEPTED.value):
            raise ValueError(f"Order {order.code} in {order.status} cannot be cancelled")

        # Restore stock atomically for each line item
        for item in order.line_items:
            await self.product_repo.restore_stock(item.product_id, item.quantity)

        updated = await self.order_repo.update_status(id, OrderStatus.CANCELLED.value)
        if updated:
            await audit_log(self.session, "order", id, "cancelled", actor_id=actor_id, ip_address=ip_address)
        return await self.order_repo.get_with_items(id)

    # ── Attach invoice ─────────────────────────────────────────────────────────

    async def attach_invoice(self, order_id: uuid.UUID, invoice_id: uuid.UUID) -> Order | None:
        return await self.order_repo.update(order_id, invoice_id=invoice_id)
