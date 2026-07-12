"""
OrderController — REST endpoints for order lifecycle (create → accept → ship → close).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.db.connection import get_session
from oms_backend.schemas.domain import (
    LineItem, Order, OrderAccept, OrderClose, OrderCreate, OrderListItem,
    OrderShip, OrderStatus, OrderUpdate, OrderWithItems, paginate,
)
from oms_backend.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _parse_actor(x_actor_id: str | None) -> uuid.UUID | None:
    """Parse X-Actor-ID header into a UUID, or return None."""
    if not x_actor_id:
        return None
    try:
        return uuid.UUID(x_actor_id)
    except ValueError:
        return None


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=OrderWithItems, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Customer places a new order.
    Workflow step 1.
    """
    svc = OrderService(session)
    try:
        order = await svc.create(data, ip_address=_client_ip(request))
        return OrderWithItems.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Read ───────────────────────────────────────────────────────────────────────

@router.get("/{order_id}", response_model=OrderWithItems)
async def get_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get an order with all line items."""
    svc = OrderService(session)
    order = await svc.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderWithItems.model_validate(order)


@router.get("/code/{code}", response_model=OrderWithItems)
async def get_order_by_code(
    code: str,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get an order by its human-readable code."""
    svc = OrderService(session)
    order = await svc.get_by_code(code)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderWithItems.model_validate(order)


@router.get("", response_model=dict)
async def list_orders(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    List orders. Can filter by status or customer.
    Order Staff and Accountant use this to find orders needing action.
    """
    svc = OrderService(session)

    if status:
        orders, total = await svc.list_by_status(status, page=page, page_size=page_size)
    elif customer_id:
        orders, total = await svc.list_for_customer(customer_id, page=page, page_size=page_size)
    else:
        orders, total = await svc.list_all(page=page, page_size=page_size)

    items = [
        OrderListItem(
            id=o.id,
            code=o.code,
            status=OrderStatus(o.status),
            total_amount=o.total_amount,
            currency=o.currency,
            created_at=o.created_at,
            customer_name=o.customer.name if o.customer else None,
        )
        for o in orders
    ]
    return paginate(items, total=total, page=page, page_size=page_size).model_dump()


# ── Update ─────────────────────────────────────────────────────────────────────

@router.put("/{order_id}", response_model=OrderWithItems)
async def update_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_actor_id: Annotated[str | None, Header()] = None,
):
    """Update shipping details or notes on a pending order."""
    svc = OrderService(session)
    try:
        order = await svc.update(order_id, data, actor_id=_parse_actor(x_actor_id), ip_address=_client_ip(request))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderWithItems.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Lifecycle: Accept ──────────────────────────────────────────────────────────

@router.post("/{order_id}/accept", response_model=OrderWithItems)
async def accept_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    data: OrderAccept | None = None,
    x_actor_id: Annotated[str | None, Header()] = None,
    x_forwarded_for: Annotated[str | None, Header(alias="X-Forwarded-For")] = None,
):
    """
    Order Staff reviews and accepts a pending order.
    Workflow step 2.
    """
    actor_uuid = _parse_actor(x_actor_id)
    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    svc = OrderService(session)
    try:
        order = await svc.accept(order_id, data, actor_id=actor_uuid, ip_address=ip)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderWithItems.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Lifecycle: Ship ────────────────────────────────────────────────────────────

@router.post("/{order_id}/ship", response_model=OrderWithItems)
async def ship_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    data: OrderShip | None = None,
    x_actor_id: Annotated[str | None, Header()] = None,
    x_forwarded_for: Annotated[str | None, Header(alias="X-Forwarded-For")] = None,
):
    """
    Order Staff marks a paid order as shipped.
    Workflow step 6.
    """
    actor_uuid = _parse_actor(x_actor_id)
    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    svc = OrderService(session)
    try:
        order = await svc.ship(order_id, data, actor_id=actor_uuid, ip_address=ip)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderWithItems.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Lifecycle: Close ───────────────────────────────────────────────────────────

@router.post("/{order_id}/close", response_model=OrderWithItems)
async def close_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    data: OrderClose | None = None,
    x_actor_id: Annotated[str | None, Header()] = None,
    x_forwarded_for: Annotated[str | None, Header(alias="X-Forwarded-For")] = None,
):
    """
    Order Staff closes a shipped/delivered order.
    Workflow step 7.
    """
    actor_uuid = _parse_actor(x_actor_id)
    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    svc = OrderService(session)
    try:
        order = await svc.close(order_id, data, actor_id=actor_uuid, ip_address=ip)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderWithItems.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Lifecycle: Cancel ──────────────────────────────────────────────────────────

@router.post("/{order_id}/cancel", response_model=OrderWithItems)
async def cancel_order(
    order_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_forwarded_for: Annotated[str | None, Header(alias="X-Forwarded-For")] = None,
):
    """Cancel a pending or accepted order (restores stock)."""
    actor_uuid = _parse_actor(x_actor_id)
    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    svc = OrderService(session)
    try:
        order = await svc.cancel(order_id, actor_id=actor_uuid, ip_address=ip)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderWithItems.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
