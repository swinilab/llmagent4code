"""
Order controller — REST endpoint handlers for order operations.

Covers the full order lifecycle: create, update items, transition status,
list, and delete. Status transitions enforce the workflow.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from oms.enums import OrderStatus
from oms.schemas.order import OrderCreate, OrderUpdate, OrderRead, OrderStatusUpdate
from oms.schemas.common import PaginatedResponse
from oms.services.order import OrderService, OrderTransitionError


class OrderController:
    """Handles order CRUD and lifecycle endpoints."""

    async def create_order(self, data: OrderCreate, session: AsyncSession) -> OrderRead:
        service = OrderService(session)
        try:
            order = await service.create_order(data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return OrderRead.model_validate(order)

    async def get_order(self, order_id: str, session: AsyncSession) -> OrderRead:
        service = OrderService(session)
        order = await service.get_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return OrderRead.model_validate(order)

    async def list_orders(self, session: AsyncSession, page: int = 1, page_size: int = 20, status: OrderStatus | None = None) -> PaginatedResponse[OrderRead]:
        service = OrderService(session)
        items, total = await service.list_orders(page=page, page_size=page_size, status=status)
        return PaginatedResponse[OrderRead].create(
            items=[OrderRead.model_validate(o) for o in items],
            total=total, page=page, page_size=page_size,
        )

    async def list_customer_orders(self, customer_id: str, session: AsyncSession, page: int = 1, page_size: int = 20) -> PaginatedResponse[OrderRead]:
        service = OrderService(session)
        items, total = await service.list_customer_orders(customer_id, page=page, page_size=page_size)
        return PaginatedResponse[OrderRead].create(
            items=[OrderRead.model_validate(o) for o in items],
            total=total, page=page, page_size=page_size,
        )

    async def update_order_items(self, order_id: str, data: OrderUpdate, session: AsyncSession) -> OrderRead:
        service = OrderService(session)
        try:
            order = await service.update_order_items(order_id, data)
        except OrderTransitionError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return OrderRead.model_validate(order)

    async def transition_status(self, order_id: str, data: OrderStatusUpdate, session: AsyncSession) -> OrderRead:
        service = OrderService(session)
        try:
            order = await service.transition_status(order_id, data)
        except OrderTransitionError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return OrderRead.model_validate(order)

    async def cancel_order(self, order_id: str, session: AsyncSession, reason: str | None = None) -> OrderRead:
        service = OrderService(session)
        try:
            order = await service.cancel_order(order_id, reason=reason)
        except OrderTransitionError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return OrderRead.model_validate(order)

    async def delete_order(self, order_id: str, session: AsyncSession) -> dict:
        service = OrderService(session)
        deleted = await service.delete_order(order_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return {"deleted": True, "id": order_id}


order_controller = OrderController()