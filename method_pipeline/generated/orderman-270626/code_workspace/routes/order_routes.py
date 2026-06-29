"""
Order Routes - API endpoints for Order operations.
Defines RESTful endpoints for order management and workflow.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.models import get_session
from controllers.order_controller import OrderController
from shared.models import (
    Order,
    OrderCreate,
    OrderUpdate,
    OrderListResponse,
    OrderStatus,
    APIResponse,
)

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("", response_model=OrderListResponse)
async def list_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all orders with pagination, optionally filtered by status or customer.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **status**: Optional filter by order status
    - **customer_id**: Optional filter by customer ID
    """
    controller = OrderController(db)
    
    if customer_id:
        return await controller.get_orders_by_customer(customer_id=customer_id, skip=skip, limit=limit)
    
    if status:
        return await controller.get_orders_by_status(status=status, skip=skip, limit=limit)
    
    return await controller.get_all_orders(skip=skip, limit=limit)


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific order by ID.
    
    - **order_id**: The unique order identifier
    """
    controller = OrderController(db)
    order = await controller.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order


@router.post("", response_model=Order, status_code=201)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new order (Customer action).
    
    - **customer_id**: Customer identifier
    - **items**: List of order items (product_id, product_name, quantity, unit_price, subtotal)
    - **total_amount**: Total order amount
    - **shipping_address**: Shipping address
    - **notes**: Optional order notes
    """
    controller = OrderController(db)
    return await controller.create_order(order_data)


@router.post("/{order_id}/accept", response_model=Order)
async def accept_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Accept an order (Order Staff action).
    Changes status from PENDING to ACCEPTED.
    
    - **order_id**: The unique order identifier
    """
    controller = OrderController(db)
    
    try:
        order = await controller.accept_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{order_id}", response_model=Order)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: AsyncSession = Depends(get_session),
):
    """
    Update an existing order.
    
    - **order_id**: The unique order identifier
    - **status**: Optional new status
    - **shipping_address**: Optional new shipping address
    - **notes**: Optional new notes
    """
    controller = OrderController(db)
    
    order = await controller.update_order(order_id, order_data)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order


@router.post("/{order_id}/ship", response_model=Order)
async def ship_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Ship an order (Order Staff action after payment).
    Changes status from PAID to SHIPPED.
    
    - **order_id**: The unique order identifier
    """
    controller = OrderController(db)
    
    try:
        order = await controller.ship_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/complete", response_model=Order)
async def complete_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Complete/close an order (Order Staff action after shipping).
    Changes status from SHIPPED to COMPLETED.
    
    - **order_id**: The unique order identifier
    """
    controller = OrderController(db)
    
    try:
        order = await controller.complete_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel", response_model=Order)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Cancel an order.
    
    - **order_id**: The unique order identifier
    """
    controller = OrderController(db)
    
    try:
        order = await controller.cancel_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{order_id}", response_model=APIResponse)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Delete an order.
    
    - **order_id**: The unique order identifier
    """
    controller = OrderController(db)
    
    success = await controller.delete_order(order_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return APIResponse(success=True, message="Order deleted successfully")
