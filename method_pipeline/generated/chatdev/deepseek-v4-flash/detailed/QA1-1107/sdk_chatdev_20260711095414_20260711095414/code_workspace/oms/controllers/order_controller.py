"""
Order controller — all order lifecycle endpoints.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.enums import PaymentMethod
from oms.domain.models import Order, OrderLineItem, Payment, Invoice
from oms.infrastructure.database import get_db
from oms.infrastructure.metrics import http_requests_total
from oms.infrastructure.rate_limiter import checkout_rate_limiter
from oms.services.order_service import OrderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


# ── Request / Response schemas ───────────────────────────────────────────────

class PlaceOrderRequest(BaseModel):
    customer_id: UUID
    line_items: list[OrderLineItem]


class SubmitPaymentRequest(BaseModel):
    order_id: UUID
    amount: Decimal = Field(..., decimal_places=2)
    method: PaymentMethod
    idempotency_key: str


class TransitionRequest(BaseModel):
    expected_version: int


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("", response_model=Order, status_code=201)
async def place_order(
    req: PlaceOrderRequest,
    db: AsyncSession = Depends(get_db),
    x_request_id: Optional[str] = Header(None),
) -> Order:
    """
    Checkout-critical: place a new order.
    Rate-limited by token bucket.
    """
    logger.info("place_order called | customer_id=%s | request_id=%s", req.customer_id, x_request_id)

    # Rate limit check
    allowed = await checkout_rate_limiter.consume()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please retry after the Retry-After period.",
            headers={"Retry-After": "1"},
        )

    service = OrderService(db)
    try:
        order = await service.place_order(req.customer_id, req.line_items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    http_requests_total.labels(method="POST", endpoint="/api/v1/orders", status="201").inc()
    return order


@router.post("/payment", response_model=Payment, status_code=201)
async def submit_payment(
    req: SubmitPaymentRequest,
    db: AsyncSession = Depends(get_db),
    x_request_id: Optional[str] = Header(None),
) -> Payment:
    """
    Checkout-critical: submit payment with idempotency.
    Rate-limited by token bucket.
    """
    logger.info("submit_payment called | order_id=%s | request_id=%s", req.order_id, x_request_id)

    allowed = await checkout_rate_limiter.consume()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please retry after the Retry-After period.",
            headers={"Retry-After": "1"},
        )

    service = OrderService(db)
    try:
        payment = await service.submit_payment(
            req.order_id, req.amount, req.method, req.idempotency_key
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Circuit breaker open — downstream unavailable, not client error
        raise HTTPException(
            status_code=503,
            detail=str(e),
            headers={"Retry-After": "30"},
        )

    http_requests_total.labels(method="POST", endpoint="/api/v1/orders/payment", status="201").inc()
    return payment


@router.get("", response_model=list[Order])
async def list_orders(
    customer_id: Optional[UUID] = Query(None, description="Filter by customer ID"),
    db: AsyncSession = Depends(get_db),
) -> list[Order]:
    """List orders, optionally filtered by customer_id."""
    service = OrderService(db)
    return await service.list_orders(customer_id)


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Get a single order by ID."""
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.post("/{order_id}/accept", response_model=Order)
async def accept_order(
    order_id: UUID,
    req: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Back-office: Order Staff accepts order."""
    service = OrderService(db)
    try:
        order = await service.accept_order(order_id, req.expected_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order


@router.post("/{order_id}/invoice", response_model=Invoice, status_code=201)
async def create_invoice(
    order_id: UUID,
    req: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> Invoice:
    """Back-office: Accountant creates invoice."""
    service = OrderService(db)
    try:
        invoice = await service.create_invoice(order_id, req.expected_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return invoice


@router.post("/{order_id}/verify-payment", response_model=Order)
async def verify_payment(
    order_id: UUID,
    req: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Back-office: Accountant verifies payment."""
    service = OrderService(db)
    try:
        order = await service.verify_payment(order_id, req.expected_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order


@router.post("/{order_id}/ship", response_model=Order)
async def ship_order(
    order_id: UUID,
    req: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Back-office: Order Staff ships order."""
    service = OrderService(db)
    try:
        order = await service.ship_order(order_id, req.expected_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Circuit breaker open — downstream unavailable
        raise HTTPException(
            status_code=503,
            detail=str(e),
            headers={"Retry-After": "30"},
        )
    return order


@router.post("/{order_id}/close", response_model=Order)
async def close_order(
    order_id: UUID,
    req: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Back-office: Order Staff closes order."""
    service = OrderService(db)
    try:
        order = await service.close_order(order_id, req.expected_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order


@router.post("/{order_id}/cancel", response_model=Order)
async def cancel_order(
    order_id: UUID,
    req: TransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Cancel order from any pre-SHIPPED state."""
    service = OrderService(db)
    try:
        order = await service.cancel_order(order_id, req.expected_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order
