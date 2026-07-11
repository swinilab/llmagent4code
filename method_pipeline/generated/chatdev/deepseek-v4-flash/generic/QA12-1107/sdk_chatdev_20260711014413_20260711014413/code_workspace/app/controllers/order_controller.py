"""
Order REST controller — full workflow.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from app.infrastructure.queue_manager import QueueManager
from app.models.enums import OrderStatus
from app.schemas.order_schema import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
)
from app.services.order_service import OrderService


def create_order_router(
    dep_service: Callable[[], OrderService],
    queue_mgr: QueueManager | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

    @router.post("", status_code=202)
    async def place_order(
        body: OrderCreate,
        service: OrderService = Depends(dep_service),
    ):
        """Step 1: Customer places order (queued for async processing)."""
        if queue_mgr is None:
            # Fallback: process synchronously (e.g. in tests without queue)
            try:
                return await service.place_order(
                    customer_id=body.customer_id,
                    items=[item.model_dump() for item in body.items],
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        enqueued = await queue_mgr.enqueue(
            task_type="place_order",
            payload={
                "customer_id": body.customer_id,
                "items": [item.model_dump() for item in body.items],
            },
            essential=True,
        )
        if not enqueued:
            raise HTTPException(status_code=503, detail="System busy, try again later")
        return {"status": "accepted", "message": "Order queued for processing"}

    @router.get("/{order_id}", response_model=OrderResponse)
    async def get_order(
        order_id: str,
        service: OrderService = Depends(dep_service),
    ):
        order = await service.get_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @router.get("", response_model=OrderListResponse)
    async def list_orders(
        status: OrderStatus | None = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        service: OrderService = Depends(dep_service),
    ):
        orders, total = await service.list_orders(status=status, skip=skip, limit=limit)
        return OrderListResponse(orders=orders, total=total)

    @router.put("/{order_id}/review", response_model=OrderResponse)
    async def review_order(
        order_id: str,
        service: OrderService = Depends(dep_service),
    ):
        """Step 2a: Order Staff reviews order."""
        try:
            return await service.review_order(order_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.put("/{order_id}/accept", response_model=OrderResponse)
    async def accept_order(
        order_id: str,
        service: OrderService = Depends(dep_service),
    ):
        """Step 2b: Order Staff accepts order."""
        try:
            return await service.accept_order(order_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.put("/{order_id}/cancel", response_model=OrderResponse)
    async def cancel_order(
        order_id: str,
        service: OrderService = Depends(dep_service),
    ):
        """Cancel an order (before shipping)."""
        try:
            return await service.cancel_order(order_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.put("/{order_id}/ship", response_model=OrderResponse)
    async def ship_order(
        order_id: str,
        service: OrderService = Depends(dep_service),
    ):
        """Step 6: Order Staff ships paid order."""
        try:
            return await service.ship_order(order_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.put("/{order_id}/close", response_model=OrderResponse)
    async def close_order(
        order_id: str,
        service: OrderService = Depends(dep_service),
    ):
        """Step 7: Order Staff closes completed order."""
        try:
            return await service.close_order(order_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return router
