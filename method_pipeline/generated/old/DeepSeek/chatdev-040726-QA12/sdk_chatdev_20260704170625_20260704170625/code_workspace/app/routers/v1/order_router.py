"""Order REST controller — v1 API.
Versioned path prefix (/v1/orders) satisfies NFR 2.2 (Interface Stability).

WorkflowError and ValueError propagate to global handlers in main.py
for ACID-compliant transaction rollback.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.models import LineItem, Order, OrderStatus
from app.services.order_service import OrderService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/orders", tags=["Orders"])


# ── Request schemas ───────────────────────────────────────────────────────────
class PlaceOrderRequest(BaseModel):
    customer_id: str
    line_items: list[LineItem]


class StatusUpdateResponse(BaseModel):
    order: Order
    message: str


# ── Customer endpoints ────────────────────────────────────────────────────────
@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
async def place_order(body: PlaceOrderRequest, db: AsyncSession = Depends(get_db)):
    """Customer places an order (Step 1).

    ValueError (invalid customer) propagates to the global exception handler
    which returns a 400 response AFTER the DB transaction is rolled back
    by get_db(), preserving ACID guarantees.
    """
    workflow = WorkflowService(db)
    return await workflow.place_order(body.customer_id, body.line_items)


@router.get("", response_model=list[Order])
async def list_orders(
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    return await svc.list_orders(status_filter)


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ── Order Staff endpoints ─────────────────────────────────────────────────────


@router.post("/{order_id}/accept", response_model=StatusUpdateResponse)
async def accept_order(order_id: str, db: AsyncSession = Depends(get_db)):
    workflow = WorkflowService(db)
    order = await workflow.accept_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=409,
            detail="Order cannot be accepted (must be PENDING)",
        )
    return StatusUpdateResponse(order=order, message="Order accepted")


@router.post("/{order_id}/ship", response_model=StatusUpdateResponse)
async def ship_order(order_id: str, db: AsyncSession = Depends(get_db)):
    workflow = WorkflowService(db)
    order = await workflow.ship_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=409,
            detail="Order cannot be shipped (must be VERIFIED/paid)",
        )
    return StatusUpdateResponse(order=order, message="Order shipped")


@router.post("/{order_id}/close", response_model=StatusUpdateResponse)
async def close_order(order_id: str, db: AsyncSession = Depends(get_db)):
    workflow = WorkflowService(db)
    order = await workflow.close_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=409,
            detail="Order cannot be closed (must be SHIPPED)",
        )
    return StatusUpdateResponse(order=order, message="Order completed")