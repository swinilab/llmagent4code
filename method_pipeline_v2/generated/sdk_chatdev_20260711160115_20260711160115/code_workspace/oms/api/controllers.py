# FastAPI route handlers (controllers) for all OMS endpoints.
#
# Versioned under /api/v1/ prefix.
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

from oms.api.schemas import (
    CustomerCreate,
    CustomerResponse,
    InvoiceRequest,
    InvoiceResponse,
    LineItemResponse,
    OrderAction,
    OrderCreate,
    OrderResponse,
    PaymentRequest,
    PaymentResponse,
    ProductCreate,
    ProductResponse,
    VerifyPaymentResponse,
)
from oms.infrastructure.database import get_db_session, get_db_session_readonly
from oms.infrastructure.retry import with_db_retry
from oms.repositories.orm_models import CustomerRepository, ProductRepository
from oms.services.order_service import OrderService, ProductService, RecommendationService

router = APIRouter(prefix="/api/v1", tags=["OMS API"])


def _get_role(x_user_role: str = Header("CUSTOMER")) -> str:
    """Extract user role from header (no auth required per spec)."""
    return x_user_role.upper()


# ===================== Customer Endpoints =====================

@router.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new customer."""
    repo = CustomerRepository(session)
    orm = await with_db_retry(repo.create, body.model_dump())
    return CustomerResponse(
        id=orm.id,
        name=orm.name,
        address=orm.address,
        phone=orm.phone,
        banking_details=orm.banking_details,
        role=orm.role,
        created_at=orm.created_at,
    )


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(
    session: AsyncSession = Depends(get_db_session_readonly),
):
    """List all customers."""
    repo = CustomerRepository(session)
    orms = await with_db_retry(repo.list_all)
    return [
        CustomerResponse(
            id=c.id, name=c.name, address=c.address, phone=c.phone,
            banking_details=c.banking_details, role=c.role, created_at=c.created_at,
        )
        for c in orms
    ]


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_db_session_readonly),
):
    """Get customer by ID."""
    repo = CustomerRepository(session)
    orm = await with_db_retry(repo.get_by_id, customer_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerResponse(
        id=orm.id, name=orm.name, address=orm.address, phone=orm.phone,
        banking_details=orm.banking_details, role=orm.role, created_at=orm.created_at,
    )


# ===================== Product Endpoints =====================

@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    body: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new product."""
    repo = ProductRepository(session)
    orm = await with_db_retry(repo.create, body.model_dump())
    return ProductResponse(
        id=orm.id, name=orm.name, description=orm.description,
        base_price=str(orm.base_price), currency=orm.currency,
        stock_available=orm.stock_available,
    )


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    session: AsyncSession = Depends(get_db_session_readonly),
):
    """List or search products."""
    svc = ProductService(session)
    if q:
        results = await svc.search_products(q)
    else:
        results = await svc.list_products()
    return [ProductResponse(**r) for r in results]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_db_session_readonly),
):
    """Get product by ID."""
    svc = ProductService(session)
    try:
        result = await svc.get_product(product_id)
        return ProductResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===================== Order Endpoints =====================

@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    body: OrderCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Step 1: Customer places order. (Checkout-critical)"""
    svc = OrderService(session)
    try:
        order = await svc.create_order(
            body.customer_id,
            [it.model_dump() for it in body.line_items],
        )
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(
    customer_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session_readonly),
):
    """List orders, optionally filtered by customer."""
    svc = OrderService(session)
    orders = await svc.list_orders(customer_id)
    return [_order_to_response(o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session_readonly),
):
    """Get order by ID."""
    svc = OrderService(session)
    try:
        order = await svc.get_order(order_id)
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/orders/{order_id}/accept", response_model=OrderResponse)
async def accept_order(
    order_id: str,
    body: OrderAction,
    session: AsyncSession = Depends(get_db_session),
    role: str = Depends(_get_role),
):
    """Step 2: Order Staff reviews & accepts. (Requires ORDER_STAFF or ACCOUNTANT role)"""
    svc = OrderService(session)
    try:
        order = await svc.accept_order(order_id, body.version, role=role)
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/invoice", response_model=InvoiceResponse)
async def invoice_order(
    order_id: str,
    body: InvoiceRequest,
    session: AsyncSession = Depends(get_db_session),
    role: str = Depends(_get_role),
):
    """Step 3: Accountant creates invoice. (Requires ACCOUNTANT role)"""
    svc = OrderService(session)
    try:
        result = await svc.invoice_order(order_id, body.version, body.billing_address, role=role)
        return InvoiceResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/pay", response_model=PaymentResponse)
async def pay_order(
    order_id: str,
    body: PaymentRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Step 4: Customer pays invoice. (Checkout-critical, idempotent)"""
    svc = OrderService(session)
    try:
        result = await svc.pay_order(
            order_id, body.amount, body.method, body.idempotency_key,
        )
        return PaymentResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{order_id}/payment", response_model=VerifyPaymentResponse)
async def verify_payment(
    order_id: str,
    session: AsyncSession = Depends(get_db_session_readonly),
):
    """Step 5: Accountant verifies payment."""
    svc = OrderService(session)
    try:
        result = await svc.verify_payment(order_id)
        return VerifyPaymentResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/orders/{order_id}/ship", response_model=OrderResponse)
async def ship_order(
    order_id: str,
    body: OrderAction,
    session: AsyncSession = Depends(get_db_session),
    role: str = Depends(_get_role),
):
    """Step 6: Order Staff ships paid order. (Requires ORDER_STAFF role)"""
    svc = OrderService(session)
    try:
        order = await svc.ship_order(order_id, body.version, role=role)
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/close", response_model=OrderResponse)
async def close_order(
    order_id: str,
    body: OrderAction,
    session: AsyncSession = Depends(get_db_session),
    role: str = Depends(_get_role),
):
    """Step 7: Order Staff closes completed order. (Requires ORDER_STAFF role)"""
    svc = OrderService(session)
    try:
        order = await svc.close_order(order_id, body.version, role=role)
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    body: OrderAction,
    session: AsyncSession = Depends(get_db_session),
):
    """Cancel an order (terminal exception state). Restores stock."""
    svc = OrderService(session)
    try:
        order = await svc.cancel_order(order_id, body.version)
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== Recommendations (Non-essential) =====================

@router.get("/recommendations/{customer_id}")
async def get_recommendations(customer_id: str):
    """Get personalized recommendations (non-essential, circuit-breaker protected)."""
    svc = RecommendationService()
    return await svc.get_recommendations(customer_id)


# ===================== Helpers =====================

def _order_to_response(order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        line_items=[
            LineItemResponse(
                product_id=it.product_id,
                product_name=it.product_name,
                quantity=it.quantity,
                unit_price=str(it.unit_price),
                currency=it.currency,
            )
            for it in order.line_items
        ],
        total_amount=str(order.total_amount),
        currency=order.currency,
        status=order.status.value,
        invoice_ref=order.invoice_ref,
        version=order.version,
        created_at=order.created_at,
        accepted_at=order.accepted_at,
        invoiced_at=order.invoiced_at,
        paid_at=order.paid_at,
        shipped_at=order.shipped_at,
        closed_at=order.closed_at,
        cancelled_at=order.cancelled_at,
    )
