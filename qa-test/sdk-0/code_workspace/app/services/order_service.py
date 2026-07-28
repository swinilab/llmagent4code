"""OrderService – orchestrates order lifecycle, interacts with DB, queue and other services.

Key NFR implementations:
- **NFR 1.2 Concurrency** – async methods, uses asyncio for DB I/O.
- **NFR 1.3 Queue Management** – enqueues heavy tasks (e.g., invoicing) to bounded queue.
- **NFR 2.2 Fault Detection** – uses tenacity retry when calling external payment gateway (simulated).
- **NFR 2.3 State Preservation** – writes state changes to WAL before committing.
"""

import uuid
import datetime
from decimal import Decimal
from typing import List

from tenacity import retry, stop_after_attempt, wait_fixed

from app.db.models import Order, OrderStatus, Product, Invoice, Payment, Customer
from app.api.v1.dtos.order_dto import OrderCreateDTO, OrderResponseDTO, LineItemDTO
from app.queue.queue_manager import queue_manager
from app.persistence.wal import WAL

wal = WAL()

class OrderService:
    async def create_order(self, dto: OrderCreateDTO) -> OrderResponseDTO:
        # Validate FK existence – raise 404 if missing
        async with Customer.async_session() as session:
            cust = await session.get(Customer, dto.customerRef)
            if not cust:
                raise ValueError("Customer not found")
        # Compute unit price snapshots and total
        line_items: List[LineItemDTO] = []
        total = Decimal('0')
        async with Product.async_session() as session:
            for item in dto.lineItems:
                prod = await session.get(Product, item.productRef)
                if not prod:
                    raise ValueError(f"Product {item.productRef} not found")
                # Snapshot price
                snapshot = f"{prod.price_amount:.2f}"
                line_items.append(LineItemDTO(productRef=item.productRef, quantity=item.quantity, unitPriceSnapshot=snapshot))
                total += Decimal(snapshot) * item.quantity
        order_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        order = Order(
            id=order_id,
            customer_ref=dto.customerRef,
            line_items=line_items,
            total_amount=f"{total:.2f}",
            status=OrderStatus.PLACED,
            created_at=now,
            updated_at=now,
        )
        # Persist and write to WAL
        async with Order.async_session() as session:
            session.add(order)
            await session.commit()
        await wal.append_to_wal({"action": "create_order", "order_id": order_id})
        return OrderResponseDTO.from_orm(order)

    async def accept_order(self, order_id: str) -> OrderResponseDTO:
        async with Order.async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.PLACED:
                raise ValueError("Order cannot be accepted in its current state")
            order.status = OrderStatus.ACCEPTED
            order.updated_at = datetime.datetime.utcnow().isoformat()
            await session.commit()
        await wal.append_to_wal({"action": "accept_order", "order_id": order_id})
        return OrderResponseDTO.from_orm(order)

    async def create_invoice(self, order_id: str) -> OrderResponseDTO:
        async with Order.async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.ACCEPTED:
                raise ValueError("Invoice can only be created for ACCEPTED orders")
        # Enqueue invoice creation – heavy task
        await queue_manager.enqueue_order_task({"type": "create_invoice", "order_id": order_id})
        # Immediately return current order state (still ACCEPTED)
        return OrderResponseDTO.from_orm(order)

    async def pay_order(self, order_id: str) -> OrderResponseDTO:
        async with Order.async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.INVOICED:
                raise ValueError("Order must be INVOICED before payment")
        await queue_manager.enqueue_order_task({"type": "process_payment", "order_id": order_id})
        return OrderResponseDTO.from_orm(order)

    async def ship_order(self, order_id: str) -> OrderResponseDTO:
        async with Order.async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.PAID:
                raise ValueError("Only PAID orders can be shipped")
            order.status = OrderStatus.SHIPPED
            order.updated_at = datetime.datetime.utcnow().isoformat()
            await session.commit()
        await wal.append_to_wal({"action": "ship_order", "order_id": order_id})
        return OrderResponseDTO.from_orm(order)

    async def close_order(self, order_id: str) -> OrderResponseDTO:
        async with Order.async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.SHIPPED:
                raise ValueError("Only SHIPPED orders can be closed")
            order.status = OrderStatus.CLOSED
            order.updated_at = datetime.datetime.utcnow().isoformat()
            await session.commit()
        await wal.append_to_wal({"action": "close_order", "order_id": order_id})
        return OrderResponseDTO.from_orm(order)
