"""
Order controller for handling order-related HTTP requests.

Provides REST API endpoints for the complete order lifecycle.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from oms.config.database import get_db_session
from oms.models.entities import OrderStatus
from oms.models.schemas import (
    OrderCreate,
    OrderResponse,
    OrderUpdateStatus,
    ErrorResponse,
    PaginatedResponse,
)
from oms.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def get_service(session=Depends(get_db_session)) -> OrderService:
    """Dependency injection for OrderService."""
    return OrderService(session)


@router.post(
    "",
    response_model=OrderResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create a new order",
    description="Customer places a new order with line items.",
)
async def create_order(
    order_data: OrderCreate,
    service: OrderService = Depends(get_service),
) -> OrderResponse:
    """
    Create a new order (Customer places order).
    
    Args:
        order_data: Order creation data including line items
        service: Order service instance
        
    Returns:
        Created order response
        
    Raises:
        HTTPException: If product not available or insufficient stock
    """
    try:
        return await service.create_order(order_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="Get all orders",
    description="Retrieve all orders with pagination support.",
)
async def get_all_orders(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: OrderService = Depends(get_service),
) -> PaginatedResponse:
    """
    Get all orders with pagination.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Order service instance
        
    Returns:
        Paginated list of orders
    """
    orders = await service.get_all_orders(limit=limit, offset=offset)
    total = await service.repository.count()
    return PaginatedResponse(
        items=orders,
        total=total,
        page=(offset // limit) + 1 if limit > 0 else 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if limit > 0 else 1,
    )


@router.get(
    "/pending",
    response_model=List[OrderResponse],
    summary="Get pending orders",
    description="Retrieve all pending orders awaiting review.",
)
async def get_pending_orders(
    limit: int = Query(default=100, ge=1, le=1000),
    service: OrderService = Depends(get_service),
) -> List[OrderResponse]:
    """
    Get all pending orders awaiting review.
    
    Args:
        limit: Maximum number of records to return
        service: Order service instance
        
    Returns:
        List of pending orders
    """
    return await service.get_pending_orders(limit=limit)


@router.get(
    "/shipping",
    response_model=List[OrderResponse],
    summary="Get orders ready for shipping",
    description="Retrieve all paid orders ready for shipping.",
)
async def get_orders_for_shipping(
    limit: int = Query(default=100, ge=1, le=1000),
    service: OrderService = Depends(get_service),
) -> List[OrderResponse]:
    """
    Get paid orders ready for shipping.
    
    Args:
        limit: Maximum number of records to return
        service: Order service instance
        
    Returns:
        List of orders ready for shipping
    """
    return await service.get_orders_for_shipping(limit=limit)


@router.get(
    "/customer/{customer_id}",
    response_model=List[OrderResponse],
    summary="Get orders by customer",
    description="Retrieve all orders for a specific customer.",
)
async def get_orders_by_customer(
    customer_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: OrderService = Depends(get_service),
) -> List[OrderResponse]:
    """
    Get orders for a specific customer.
    
    Args:
        customer_id: Customer ID
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Order service instance
        
    Returns:
        List of customer orders
    """
    return await service.get_orders_by_customer(customer_id, limit=limit, offset=offset)


@router.get(
    "/status/{status}",
    response_model=List[OrderResponse],
    summary="Get orders by status",
    description="Retrieve orders filtered by status.",
)
async def get_orders_by_status(
    status: OrderStatus,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: OrderService = Depends(get_service),
) -> List[OrderResponse]:
    """
    Get orders by status.
    
    Args:
        status: Order status to filter by
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Order service instance
        
    Returns:
        List of orders with the specified status
    """
    return await service.get_orders_by_status(status, limit=limit, offset=offset)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get order by ID",
    description="Retrieve a specific order by its ID.",
)
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_service),
) -> OrderResponse:
    """
    Get order by ID.
    
    Args:
        order_id: Order ID
        service: Order service instance
        
    Returns:
        Order response
        
    Raises:
        HTTPException: If order not found
    """
    order = await service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.post(
    "/{order_id}/review",
    response_model=OrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Review order",
    description="Order Staff reviews and accepts/rejects an order.",
)
async def review_order(
    order_id: int,
    accept: bool = Query(..., description="Accept (true) or reject (false)"),
    notes: str = Query(None, description="Review notes"),
    service: OrderService = Depends(get_service),
) -> OrderResponse:
    """
    Review and accept/reject an order (Order Staff action).
    
    Args:
        order_id: Order ID
        accept: True to accept, False to reject
        notes: Optional notes for the review
        service: Order service instance
        
    Returns:
        Updated order response
        
    Raises:
        HTTPException: If order not found or not in PENDING status
    """
    try:
        order = await service.review_order(order_id, accept, notes)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Update order status",
    description="Update order status with validation.",
)
async def update_order_status(
    order_id: int,
    status_update: OrderUpdateStatus,
    service: OrderService = Depends(get_service),
) -> OrderResponse:
    """
    Update order status.
    
    Args:
        order_id: Order ID
        status_update: Status update data
        service: Order service instance
        
    Returns:
        Updated order response
        
    Raises:
        HTTPException: If order not found
    """
    order = await service.update_order_status(order_id, status_update)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.post(
    "/{order_id}/ship",
    response_model=OrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Ship order",
    description="Order Staff ships a paid order.",
)
async def ship_order(
    order_id: int,
    service: OrderService = Depends(get_service),
) -> OrderResponse:
    """
    Ship a paid order (Order Staff action).
    
    Args:
        order_id: Order ID
        service: Order service instance
        
    Returns:
        Updated order response
        
    Raises:
        HTTPException: If order not found or not in PAID status
    """
    try:
        order = await service.ship_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{order_id}/complete",
    response_model=OrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Complete order",
    description="Order Staff closes a shipped order.",
)
async def complete_order(
    order_id: int,
    service: OrderService = Depends(get_service),
) -> OrderResponse:
    """
    Complete a shipped order (Order Staff action).
    
    Args:
        order_id: Order ID
        service: Order service instance
        
    Returns:
        Updated order response
        
    Raises:
        HTTPException: If order not found or not in SHIPPED status
    """
    try:
        order = await service.complete_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Cancel order",
    description="Cancel an order and restore stock.",
)
async def cancel_order(
    order_id: int,
    service: OrderService = Depends(get_service),
) -> OrderResponse:
    """
    Cancel an order and restore stock.
    
    Args:
        order_id: Order ID
        service: Order service instance
        
    Returns:
        Updated order response
        
    Raises:
        HTTPException: If order not found or cannot be cancelled
    """
    try:
        order = await service.cancel_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/analytics/revenue",
    response_model=dict,
    summary="Get total revenue",
    description="Get total revenue from completed orders.",
)
async def get_total_revenue(
    service: OrderService = Depends(get_service),
) -> dict:
    """
    Get total revenue from completed orders.
    
    Args:
        service: Order service instance
        
    Returns:
        Total revenue amount
    """
    revenue = await service.get_total_revenue()
    return {"total_revenue": revenue}
