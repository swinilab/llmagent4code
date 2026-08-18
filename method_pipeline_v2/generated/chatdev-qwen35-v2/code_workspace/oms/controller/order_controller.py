"""
Order controller with REST endpoints
Implements NFR 2.1 Exception Detection via validation and error handling
Implements NFR 2.4 Transactions via service layer
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from oms.infrastructure.database import get_async_session
from oms.service.order_service import OrderService
from oms.domain.models import Order, OrderCreate, OrderUpdate, OrderStatus
from oms.infrastructure.exceptions import NotFoundException, ConflictException
from oms.infrastructure.event.rate_limiter import RateLimiter

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

def get_order_service(session: AsyncSession = Depends(get_async_session)) -> OrderService:
    """Get order service instance"""
    return OrderService(session)

@router.get("", response_model=List[Order])
async def list_orders(
    service: OrderService = Depends(get_order_service)
):
    """List all orders"""
    return await service.get_all()

@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    service: OrderService = Depends(get_order_service)
):
    """Get order by ID"""
    return await service.get_by_id(order_id)

@router.get("/customer/{customer_id}", response_model=List[Order])
async def get_orders_by_customer(
    customer_id: str,
    service: OrderService = Depends(get_order_service)
):
    """Get orders by customer ID"""
    return await service.get_by_customer(customer_id)

@router.get("/status/{status}", response_model=List[Order])
async def get_orders_by_status(
    status: OrderStatus,
    service: OrderService = Depends(get_order_service)
):
    """Get orders by status"""
    return await service.get_by_status(status)

@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    service: OrderService = Depends(get_order_service)
):
    """
    Create new order (Customer)
    NFR 1.1: Rate limited
    NFR 2.4: Transactional
    """
    # Check rate limit (NFR 1.1)
    rate_limiter = RateLimiter.get_instance()
    if not await rate_limiter.is_allowed("order_create"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return await service.create(order)

@router.put("/{order_id}/status", response_model=Order)
async def update_order_status(
    order_id: str,
    update: OrderUpdate,
    service: OrderService = Depends(get_order_service)
):
    """
    Update order status (Order Staff)
    NFR 2.4: Transactional state machine
    """
    return await service.update_status(order_id, update)

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: str,
    service: OrderService = Depends(get_order_service)
):
    """Delete order"""
    success = await service.delete(order_id)
    if not success:
        raise NotFoundException(f"Order {order_id} not found")

order_router = router
