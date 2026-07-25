"""
Order service — full lifecycle orchestration.
"""
from __future__ import annotations

from app.models.entities import Order, OrderItem
from app.models.enums import OrderStatus
from app.repositories.customer_repo import CustomerRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.order_schema import (
    OrderItemResponse,
    OrderResponse,
)


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        product_repo: ProductRepository,
        customer_repo: CustomerRepository,
    ) -> None:
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._customer_repo = customer_repo

    async def place_order(
        self,
        customer_id: str,
        items: list[dict],
    ) -> OrderResponse:
        """Customer places a new order (step 1)."""
        # Validate customer exists
        customer = await self._customer_repo.get(customer_id)
        if customer is None:
            raise ValueError(f"Customer {customer_id} not found")

        line_items_data = []
        total = 0.0
        currency = "USD"

        for item in items:
            product = await self._product_repo.get(item["product_id"])
            if product is None:
                raise ValueError(f"Product {item['product_id']} not found")
            if product.stock_quantity < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for product '{product.name}': "
                    f"requested {item['quantity']}, available {product.stock_quantity}"
                )
            unit_price = product.base_price
            qty = item["quantity"]
            line_total = round(unit_price * qty, 2)
            total += line_total
            currency = product.currency
            line_items_data.append({
                "product_id": product.id,
                "quantity": qty,
                "unit_price": unit_price,
                "total_price": line_total,
            })

        total = round(total, 2)
        order = await self._order_repo.create(
            customer_id=customer_id,
            status=OrderStatus.PENDING,
            total_amount=total,
            currency=currency,
        )

        for li in line_items_data:
            oi = OrderItem(
                order_id=order.id,
                product_id=li["product_id"],
                quantity=li["quantity"],
                unit_price=li["unit_price"],
                total_price=li["total_price"],
            )
            self._order_repo.session.add(oi)
            # Decrement stock
            product = await self._product_repo.get(li["product_id"])
            if product:
                product.stock_quantity -= li["quantity"]

        await self._order_repo.session.flush()
        return await self._build_response(order.id)

    async def review_order(self, order_id: str) -> OrderResponse:
        """Order Staff reviews order (step 2a)."""
        order = await self._order_repo.get_with_items(order_id)
        if order is None:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot review order in status {order.status.value}")
        order.status = OrderStatus.REVIEWED
        await self._order_repo.session.flush()
        return await self._build_response(order_id)

    async def accept_order(self, order_id: str) -> OrderResponse:
        """Order Staff accepts order (step 2b)."""
        order = await self._order_repo.get_with_items(order_id)
        if order is None:
            raise ValueError("Order not found")
        if order.status != OrderStatus.REVIEWED:
            raise ValueError(f"Cannot accept order in status {order.status.value}")
        order.status = OrderStatus.ACCEPTED
        await self._order_repo.session.flush()
        return await self._build_response(order_id)

    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel an order at any stage before shipping."""
        order = await self._order_repo.get_with_items(order_id)
        if order is None:
            raise ValueError("Order not found")
        cancellable = {
            OrderStatus.PENDING,
            OrderStatus.REVIEWED,
            OrderStatus.ACCEPTED,
            OrderStatus.INVOICED,
        }
        if order.status not in cancellable:
            raise ValueError(
                f"Cannot cancel order in status {order.status.value}. "
                f"Only cancellable before shipping."
            )
        order.status = OrderStatus.CANCELLED
        # Restore stock for cancelled orders
        for li in order.line_items:
            product = await self._product_repo.get(li.product_id)
            if product:
                product.stock_quantity += li.quantity
        await self._order_repo.session.flush()
        return await self._build_response(order_id)

    async def ship_order(self, order_id: str) -> OrderResponse:
        """Order Staff ships paid order (step 6)."""
        order = await self._order_repo.get_with_items(order_id)
        if order is None:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PAID:
            raise ValueError(f"Cannot ship order in status {order.status.value}")
        order.status = OrderStatus.SHIPPED
        await self._order_repo.session.flush()
        return await self._build_response(order_id)

    async def close_order(self, order_id: str) -> OrderResponse:
        """Order Staff closes completed order (step 7)."""
        order = await self._order_repo.get_with_items(order_id)
        if order is None:
            raise ValueError("Order not found")
        if order.status != OrderStatus.SHIPPED:
            raise ValueError(f"Cannot close order in status {order.status.value}")
        order.status = OrderStatus.CLOSED
        await self._order_repo.session.flush()
        return await self._build_response(order_id)

    async def get_order(self, order_id: str) -> OrderResponse | None:
        return await self._build_response(order_id)

    async def list_orders(
        self,
        status: OrderStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[OrderResponse], int]:
        orders, total = await self._order_repo.list_by_status(
            status=status, skip=skip, limit=limit
        )
        results = []
        for o in orders:
            resp = await self._order_to_response(o)
            results.append(resp)
        return results, total

    async def _build_response(self, order_id: str) -> OrderResponse | None:
        order = await self._order_repo.get_with_items(order_id)
        if order is None:
            return None
        return await self._order_to_response(order)

    async def _order_to_response(self, order: Order) -> OrderResponse:
        items = []
        for li in order.line_items:
            product_name = li.product.name if li.product else ""
            items.append(
                OrderItemResponse(
                    id=li.id,
                    product_id=li.product_id,
                    product_name=product_name,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    total_price=li.total_price,
                )
            )
        customer_name = order.customer.name if order.customer else ""
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            customer_name=customer_name,
            status=order.status,
            total_amount=order.total_amount,
            currency=order.currency,
            invoice_id=order.invoice.id if order.invoice else None,
            line_items=items,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
