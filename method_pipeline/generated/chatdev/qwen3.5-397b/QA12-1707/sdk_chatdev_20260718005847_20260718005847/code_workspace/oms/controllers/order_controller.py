"""
Order REST API controller.
Handles HTTP requests for order operations and workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms.config.database import get_db
from oms.models.order import OrderCreate, OrderReviewRequest, OrderShipRequest, OrderResponse, OrderStatus
from oms.services.order_service import OrderService

order_router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@order_router.get("", response_model=List[OrderResponse])
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: OrderStatus = Query(None),
    customer_id: int = Query(None, gt=0),
    db: AsyncSession = Depends(get_db)
):
    """Get all orders with optional filters."""
    service = OrderService(db)
    if customer_id:
        return await service.get_orders_by_customer(customer_id, skip=skip, limit=limit)
    if status:
        return await service.get_orders_by_status(status, skip=skip, limit=limit)
    return await service.get_all_orders(skip=skip, limit=limit)


@order_router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Get an order by ID."""
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@order_router.post("", response_model=OrderResponse, status_code=201)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new order (Customer workflow step 1).
    """
    service = OrderService(db)
    try:
        return await service.create_order(order_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.post("/{order_id}/review", response_model=OrderResponse)
async def review_order(
    order_id: int,
    review_data: OrderReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Review and accept/reject an order (Order Staff workflow step 2).
    """
    service = OrderService(db)
    try:
        order = await service.review_order(order_id, accept=review_data.accept, notes=review_data.notes)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.post("/{order_id}/accept", response_model=OrderResponse)
async def accept_order(
    order_id: int,
    notes: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Accept an order (convenience endpoint)."""
    service = OrderService(db)
    try:
        order = await service.accept_order(order_id, notes=notes)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.post("/{order_id}/reject", response_model=OrderResponse)
async def reject_order(
    order_id: int,
    notes: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Reject an order (convenience endpoint)."""
    service = OrderService(db)
    try:
        order = await service.reject_order(order_id, notes=notes)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.post("/{order_id}/ship", response_model=OrderResponse)
async def ship_order(
    order_id: int,
    ship_data: OrderShipRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark order for shipping and ship (Order Staff workflow step 6).
    """
    service = OrderService(db)
    try:
        order = await service.mark_order_for_shipping(order_id, notes=ship_data.notes)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order = await service.mark_order_shipped(order_id, notes=ship_data.notes)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.post("/{order_id}/complete", response_model=OrderResponse)
async def complete_order(
    order_id: int,
    notes: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete/close an order (Order Staff workflow step 7).
    """
    service = OrderService(db)
    try:
        order = await service.complete_order(order_id, notes=notes)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    notes: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an order."""
    service = OrderService(db)
    try:
        order = await service.cancel_order(order_id, notes=notes)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_db)
):
    """Update order status directly."""
    service = OrderService(db)
    order = await service.update_order_status(order_id, status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@order_router.get("/count")
async def get_order_count(db: AsyncSession = Depends(get_db)):
    """Get total number of orders."""
    service = OrderService(db)
    return {"count": await service.get_order_count()}


@order_router.get("/pending/count")
async def get_pending_orders_count(db: AsyncSession = Depends(get_db)):
    """Get count of pending orders for queue management."""
    service = OrderService(db)
    return {"pending_count": await service.get_pending_orders_count()}
