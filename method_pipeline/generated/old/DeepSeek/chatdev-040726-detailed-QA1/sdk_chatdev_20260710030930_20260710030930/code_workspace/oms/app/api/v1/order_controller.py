"""Order REST controller with rate limiting and backpressure on checkout.

Checkout endpoints (place_order, submit_payment) are rate-limited via the
token bucket and are subject to NFR 1.1's 300ms p95 latency target.
Back-office endpoints (accept, invoice, verify, ship, close) have a relaxed
p95 ≤ 1s target.
"""

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.api.dependencies import get_order_service
from app.domain.models import Order
from app.infrastructure.circuit_breaker import CircuitBreakerOpenError
from app.services.order_service import OrderService
from app.infrastructure.rate_limiter import TokenBucketResult, checkout_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


# ── Request/Response Models ──────────────────────────────────────────────

class LineItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class PlaceOrderRequest(BaseModel):
    customer_id: str
    line_items: list[LineItemRequest]


class AcceptOrderRequest(BaseModel):
    order_id: str


class CreateInvoiceRequest(BaseModel):
    order_id: str
    customer_name: str
    customer_address: str
    billing_info: str


class SubmitPaymentRequest(BaseModel):
    order_id: str
    amount: str
    method: str
    idempotency_key: str


class ShipOrderRequest(BaseModel):
    order_id: str


class CloseOrderRequest(BaseModel):
    order_id: str


class CancelOrderRequest(BaseModel):
    order_id: str


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    line_items: list[Any]
    subtotal: str
    tax_amount: str
    total_amount: str
    status: str
    invoice_ref: str | None
    version: int
    created_at: str
    updated_at: str
    accepted_at: str | None
    invoiced_at: str | None
    paid_at: str | None
    shipped_at: str | None
    closed_at: str | None
    cancelled_at: str | None


def _order_to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=str(order.id),
        customer_id=str(order.customer_id),
        line_items=[li.model_dump() for li in order.line_items],
        subtotal=str(order.subtotal),
        tax_amount=str(order.tax_amount),
        total_amount=str(order.total_amount),
        status=order.status.value,
        invoice_ref=str(order.invoice_ref) if order.invoice_ref else None,
        version=order.version,
        created_at=order.created_at.isoformat(),
        updated_at=order.updated_at.isoformat(),
        accepted_at=order.accepted_at.isoformat() if order.accepted_at else None,
        invoiced_at=order.invoiced_at.isoformat() if order.invoiced_at else None,
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        shipped_at=order.shipped_at.isoformat() if order.shipped_at else None,
        closed_at=order.closed_at.isoformat() if order.closed_at else None,
        cancelled_at=order.cancelled_at.isoformat() if order.cancelled_at else None,
    )


def _check_rate_limit() -> None:
    """Check rate limit and raise HTTP 429 if exceeded."""
    result: TokenBucketResult = checkout_rate_limiter.consume()
    if not result.allowed:
        retry_after = max(1, int(result.retry_after_seconds))
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please retry later.",
            headers={"Retry-After": str(retry_after)},
        )


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/place", response_model=OrderResponse, status_code=201)
async def place_order(
    request: Request,
    body: PlaceOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Place a new order (checkout-critical, rate-limited)."""
    _check_rate_limit()
    try:
        line_items_data = [item.model_dump() for item in body.line_items]
        order = await order_service.place_order(
            customer_id=UUID(body.customer_id),
            line_items_data=line_items_data,
        )
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accept", response_model=OrderResponse)
async def accept_order(
    body: AcceptOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Order Staff accepts an order (back-office)."""
    try:
        order = await order_service.accept_order(UUID(body.order_id))
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/invoice", response_model=dict)
async def create_invoice(
    body: CreateInvoiceRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Accountant creates an invoice (back-office)."""
    try:
        invoice = await order_service.create_invoice(
            order_id=UUID(body.order_id),
            customer_name=body.customer_name,
            customer_address=body.customer_address,
            billing_info=body.billing_info,
        )
        return {"id": str(invoice.id), "order_id": str(invoice.order_id), "status": invoice.status.value}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/pay", response_model=dict)
async def submit_payment(
    body: SubmitPaymentRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Customer pays invoice (checkout-critical, rate-limited)."""
    _check_rate_limit()
    try:
        payment = await order_service.submit_payment(
            order_id=UUID(body.order_id),
            amount=Decimal(body.amount),
            method=body.method,
            idempotency_key=body.idempotency_key,
        )
        return {
            "id": str(payment.id),
            "order_id": str(payment.order_id),
            "status": payment.status.value,
            "amount": str(payment.amount),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CircuitBreakerOpenError as e:
        logger.warning("Payment gateway circuit breaker open: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Payment service temporarily unavailable. Please retry later.",
            headers={"Retry-After": "30"},
        )

@router.post("/verify", response_model=OrderResponse)
async def verify_payment(
    body: AcceptOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Accountant verifies payment (back-office)."""
    try:
        order = await order_service.verify_payment(UUID(body.order_id))
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ship", response_model=OrderResponse)
async def ship_order(
    body: ShipOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Order Staff ships paid order (back-office)."""
    try:
        order = await order_service.ship_order(UUID(body.order_id))
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CircuitBreakerOpenError as e:
        logger.warning("Shipping API circuit breaker open: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Shipping service temporarily unavailable. Please retry later.",
            headers={"Retry-After": "30"},
        )


@router.post("/close", response_model=OrderResponse)
async def close_order(
    body: CloseOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Order Staff closes completed order (back-office)."""
    try:
        order = await order_service.close_order(UUID(body.order_id))
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cancel", response_model=OrderResponse)
async def cancel_order(
    body: CancelOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Cancel an order (allowed from any pre-SHIPPED state)."""
    try:
        order = await order_service.cancel_order(UUID(body.order_id))
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """Get order by ID."""
    order = await order_service.get_order(UUID(order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_response(order)


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    order_service: OrderService = Depends(get_order_service),
) -> Any:
    """List all orders with pagination."""
    orders = await order_service.list_orders(skip, limit)
    return [_order_to_response(o) for o in orders]
