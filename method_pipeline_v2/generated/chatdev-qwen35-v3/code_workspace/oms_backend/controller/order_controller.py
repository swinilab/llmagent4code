"""
Order REST API controller with workflow endpoints
Implements validation, state machine, and workflow actions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from oms_backend.repository.base import get_db
from oms_backend.service.order_service import OrderService
from oms_backend.domain.schemas import OrderCreate, OrderResponse, LineItemResponse
from oms_backend.domain.models import Order, OrderStatus

order_router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def order_to_response(order: Order) -> OrderResponse:

def order_to_response(order: Order) -> OrderResponse:
    """Convert Order model to response schema"""
    return OrderResponse(
        id=order.id,
        customerRef=order.customer_ref,
        lineItems=[
            LineItemResponse(
                productRef=item["productRef"],
                quantity=item["quantity"],
                unitPriceSnapshot=item["unitPriceSnapshot"]
            )
            for item in order.line_items
        ],
        totalAmount=float(order.total_amount),
        status=order.status,
        invoiceRef=order.invoice_ref,
        createdAt=order.created_at,
        updatedAt=order.updated_at
    )


def validate_uuid_id(order_id: str) -> None:
    """Validate UUID format, raise 400 if invalid"""
    try:
        uuid.UUID(order_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")


@order_router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Create a new order"""
    service = OrderService(session)
    try:
        order = await service.create_order(data)
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@order_router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Get order by ID"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_to_response(order)


@order_router.get("", response_model=List[OrderResponse])
async def get_all_orders(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
) -> List[OrderResponse]:
    """Get all orders with pagination"""
    service = OrderService(session)
    orders = await service.get_all_orders(limit, offset)
    return [order_to_response(o) for o in orders]


@order_router.post("/{order_id}/accept", response_model=OrderResponse)
async def accept_order(
    order_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Accept order (Order Staff action: PLACED -> ACCEPTED)"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    try:
        order = await service.accept_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@order_router.post("/{order_id}/invoice", response_model=OrderResponse)
async def invoice_order(
    order_id: str,
    invoice_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Set invoice reference (Accountant action: ACCEPTED -> INVOICED)"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    try:
        order = await service.invoice_order(order_id, invoice_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@order_router.post("/{order_id}/mark-paid", response_model=OrderResponse)
async def mark_order_paid(
    order_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Mark order as paid (INVOICED -> PAID)"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    try:
        order = await service.mark_order_paid(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@order_router.post("/{order_id}/verify", response_model=OrderResponse)
async def verify_order(
    order_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Verify order (Accountant action: PAID -> VERIFIED)"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    try:
        order = await service.verify_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@order_router.post("/{order_id}/ship", response_model=OrderResponse)
async def ship_order(
    order_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Ship order (Order Staff action: VERIFIED -> SHIPPED)"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    try:
        order = await service.ship_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@order_router.post("/{order_id}/close", response_model=OrderResponse)
async def close_order(
    order_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Close order (Order Staff action: SHIPPED -> CLOSED)"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    try:
        order = await service.close_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@order_router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Cancel order (any state -> CANCELLED)"""
    validate_uuid_id(order_id)
    
    service = OrderService(session)
    try:
        order = await service.cancel_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
