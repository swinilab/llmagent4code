"""
Order REST controller — checkout is a hot path (NFR 1.1, p95 ≤ 300 ms).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DomainError
from app.domain.schemas import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    PaginatedResponse,
)
from app.infrastructure.database import get_db
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_db),
):
    """Place a new order (checkout journey — hot path).

    Rate limiting is applied by the RateLimiterMiddleware (not by a
    per-endpoint decorator) to avoid double rate-limiting.
    """
    svc = OrderService(session)
    try:
        order = await svc.create_order(data)
        return order
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_db),
):
    svc = OrderService(session)
    try:
        return await svc.get_order(order_id)
    except DomainError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=PaginatedResponse)
async def list_orders(
    customer_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    svc = OrderService(session)
    items, total = await svc.list_orders(customer_id, page, page_size)
    return PaginatedResponse(
        items=[OrderResponse.model_validate(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Transition order status (Order Staff / Accountant actions)."""
    svc = OrderService(session)
    try:
        return await svc.update_status(order_id, data)
    except DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
