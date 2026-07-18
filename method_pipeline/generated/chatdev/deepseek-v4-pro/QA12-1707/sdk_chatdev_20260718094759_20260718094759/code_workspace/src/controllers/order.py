"""
Order REST controller.

Endpoints:
  POST   /api/v1/orders              — place order
  GET    /api/v1/orders              — list orders
  GET    /api/v1/orders/{id}         — get order
  GET    /api/v1/orders/customer/{id} — orders by customer
  GET    /api/v1/orders/status/{s}   — orders by status
  PATCH  /api/v1/orders/{id}/status  — transition status
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from src.services.order import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def place_order(payload: OrderCreate, session: AsyncSession = Depends(get_session)):
    """Customer places a new order."""
    svc = OrderService(session)
    order = await svc.create(payload)
    return order


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all orders with pagination."""
    svc = OrderService(session)
    return await svc.list_all(limit=limit, offset=offset)


@router.get("/customer/{customer_id}", response_model=list[OrderResponse])
async def orders_by_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List orders for a specific customer."""
    svc = OrderService(session)
    return await svc.list_by_customer(customer_id)


@router.get("/status/{status}", response_model=list[OrderResponse])
async def orders_by_status(
    status: str,
    session: AsyncSession = Depends(get_session),
):
    """List orders filtered by status."""
    svc = OrderService(session)
    return await svc.list_by_status(status)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, session: AsyncSession = Depends(get_session)):
    """Retrieve an order by ID."""
    svc = OrderService(session)
    return await svc.get(order_id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Transition an order to a new status."""
    svc = OrderService(session)
    return await svc.transition_status(order_id, payload.status)
