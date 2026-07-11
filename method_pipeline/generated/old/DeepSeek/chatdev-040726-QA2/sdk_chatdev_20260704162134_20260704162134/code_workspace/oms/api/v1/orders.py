"""
Order REST endpoints (v1) — full lifecycle.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oms.domain.models import Order, CreateOrderRequest, StaffActionRequest, CancelOrderRequest
from oms.service.order_service import OrderService
from oms.api.deps import get_order_service

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
def place_order(
    request: CreateOrderRequest,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Step 1: Customer places an order."""
    try:
        return service.place_order(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{order_id}/accept", response_model=Order)
def accept_order(
    order_id: UUID,
    request: StaffActionRequest,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Step 2: Order Staff reviews and accepts an order."""
    try:
        return service.accept_order(order_id, request.staff_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{order_id}/ship", response_model=Order)
def ship_order(
    order_id: UUID,
    request: StaffActionRequest,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Step 6: Order Staff ships a paid order."""
    try:
        return service.ship_order(order_id, request.staff_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{order_id}/close", response_model=Order)
def close_order(
    order_id: UUID,
    request: StaffActionRequest,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Step 7: Order Staff closes a completed order."""
    try:
        return service.close_order(order_id, request.staff_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{order_id}/cancel", response_model=Order)
def cancel_order(
    order_id: UUID,
    request: CancelOrderRequest,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Cancel an order at any stage before completion."""
    try:
        return service.cancel_order(order_id, request.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[Order])
def list_orders(
    customer_id: UUID | None = None,
    service: OrderService = Depends(get_order_service),
) -> list[Order]:
    """List orders, optionally filtered by customer_id."""
    if customer_id:
        return service.list_by_customer(customer_id)
    return service.list_all()


@router.get("/{order_id}", response_model=Order)
def get_order(
    order_id: UUID,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Get an order by ID."""
    order = service.get_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order
