"""
Order API endpoints — the core of the OMS.

Implements the full order lifecycle:
1. POST /orders — Customer places order (CREATED)
2. POST /orders/{id}/transition — Order Staff reviews & accepts (ACCEPTED)
3. POST /orders/{id}/transition — Accountant creates invoice (INVOICED)
4. POST /orders/{id}/transition — Customer pays (PAID)
5. POST /orders/{id}/transition — Order Staff ships (SHIPPED)
6. POST /orders/{id}/transition — Order Staff closes (CLOSED)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.enums import OrderStatus
from app.domain.models import Order
from app.domain.schemas import OrderCreate, OrderResponse, OrderTransitionRequest
from app.domain.state_machine import TransitionEvent
from app.infrastructure.database import get_db_session
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Order:
    """Step 1: Customer places an order."""
    service = OrderService(session)
    return await service.create_order(data)


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[Order]:
    """List orders, optionally filtered by status or customer."""
    service = OrderService(session)
    if status:
        try:
            order_status = OrderStatus(status.upper())
        except ValueError:
            raise ValueError(f"Invalid status: {status}")
        return await service.list_orders_by_status(order_status)
    if customer_id:
        return await service.list_orders_by_customer(customer_id)
    # Return all orders (paginated in production)
    return await service.list_all_orders()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Order:
    """Get order details by ID."""
    service = OrderService(session)
    order = await service.get_order(order_id)
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    return order


@router.post("/{order_id}/transition", response_model=OrderResponse)
async def transition_order(
    order_id: uuid.UUID,
    request: OrderTransitionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Order:
    """
    Apply a state transition to an order.

    This endpoint handles all workflow steps:
    - "review_accept"  (CREATED → ACCEPTED)  — Order Staff
    - "create_invoice" (ACCEPTED → INVOICED) — Accountant
    - "pay"            (INVOICED → PAID)     — Customer
    - "ship"           (PAID → SHIPPED)      — Order Staff
    - "close"          (SHIPPED → CLOSED)    — Order Staff
    - "cancel"         (any → CANCELLED)     — Any role
    """
    try:
        event = TransitionEvent(request.event)
    except ValueError:
        raise ValueError(f"Invalid transition event: {request.event}")

    service = OrderService(session)
    return await service.transition_order(
        order_id,
        event,
        invoice_ref=request.invoice_ref,
    )
