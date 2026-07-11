"""
Controllers - REST endpoint handlers with request validation and response mapping.
Each controller maps to a router prefix and delegates to the service layer.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.domain import Order
from app.domain import OrderStatus
from app.infrastructure import CircuitBreakerError
from app.schemas import (
    CustomerCreate,
    CustomerResponse,
    InvoiceCreate,
    InvoiceResponse,
    LineItemResponse,
    OrderCreate,
    OrderResponse,
    PaymentCreate,
    PaymentResponse,
    PaymentVerification,
    ProductCreate,
    ProductResponse,
)
from app.services import CustomerService, OrderService, ProductService

# ---------------------------------------------------------------------------
# Customer Controller
# ---------------------------------------------------------------------------
customer_router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])


@customer_router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, session: Session = Depends(get_session)):
    svc = CustomerService(session)
    customer = svc.register(
        name=body.name,
        address=body.address,
        phone=body.phone,
        banking_details=body.banking_details,
        role=body.role,
    )
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        address=customer.address,
        phone=customer.phone,
        banking_details=customer.banking_details,
        role=customer.role,
    )


@customer_router.get("", response_model=list[CustomerResponse])
def list_customers(session: Session = Depends(get_session)):
    svc = CustomerService(session)
    customers = svc.list_all()
    return [
        CustomerResponse(
            id=c.id, name=c.name, address=c.address, phone=c.phone,
            banking_details=c.banking_details, role=c.role,
        )
        for c in customers
    ]


@customer_router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: UUID, session: Session = Depends(get_session)):
    svc = CustomerService(session)
    customer = svc.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerResponse(
        id=customer.id, name=customer.name, address=customer.address,
        phone=customer.phone, banking_details=customer.banking_details,
        role=customer.role,
    )


# ---------------------------------------------------------------------------
# Product Controller
# ---------------------------------------------------------------------------
product_router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@product_router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductCreate, session: Session = Depends(get_session)):
    svc = ProductService(session)
    product = svc.create(
        description=body.description,
        base_price=body.base_price,
        currency=body.currency,
    )
    return ProductResponse(
        id=product.id,
        description=product.description,
        base_price=product.base_price,
        currency=product.currency,
    )


@product_router.get("", response_model=list[ProductResponse])
def list_products(session: Session = Depends(get_session)):
    svc = ProductService(session)
    products = svc.list_all()
    return [
        ProductResponse(
            id=p.id, description=p.description,
            base_price=p.base_price, currency=p.currency,
        )
        for p in products
    ]


@product_router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, session: Session = Depends(get_session)):
    svc = ProductService(session)
    product = svc.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(
        id=product.id, description=product.description,
        base_price=product.base_price, currency=product.currency,
    )


# ---------------------------------------------------------------------------
# Order Controller
# ---------------------------------------------------------------------------
order_router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@order_router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(body: OrderCreate, session: Session = Depends(get_session)):
    """Step 1: Customer places an order."""
    svc = OrderService(session)
    items = [
        {
            "product_id": str(li.product_id),
            "quantity": li.quantity,
            "unit_price": str(li.unit_price),
            "currency": li.currency,
        }
        for li in body.line_items
    ]
    try:
        order = svc.place_order(customer_id=body.customer_id, items=items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CircuitBreakerError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return _order_to_response(order)


@order_router.get("", response_model=list[OrderResponse])
def list_orders(
    status: Optional[OrderStatus] = Query(None),
    session: Session = Depends(get_session),
):
    svc = OrderService(session)
    orders = svc.list_orders(status)
    return [_order_to_response(o) for o in orders]


@order_router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: UUID, session: Session = Depends(get_session)):
    svc = OrderService(session)
    order = svc.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_response(order)


@order_router.patch("/{order_id}/accept", response_model=OrderResponse)
def accept_order(order_id: UUID, session: Session = Depends(get_session)):
    """Step 2: Order Staff accepts a pending order."""
    svc = OrderService(session)
    try:
        order = svc.accept_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_response(order)


@order_router.post("/{order_id}/invoice", response_model=InvoiceResponse)
def create_invoice(
    order_id: UUID,
    body: InvoiceCreate,
    session: Session = Depends(get_session),
):
    """Step 3: Accountant creates an invoice for an accepted order."""
    svc = OrderService(session)
    try:
        invoice = svc.create_invoice(
            order_id=order_id,
            billing_name=body.billing_name,
            billing_address=body.billing_address,
            due_days=body.due_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CircuitBreakerError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not invoice:
        raise HTTPException(status_code=404, detail="Order not found")
    return InvoiceResponse(
        id=invoice.id,
        order_id=invoice.order_id,
        billing_name=invoice.billing_name,
        billing_address=invoice.billing_address,
        total_amount=invoice.total_amount,
        currency=invoice.currency,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status=invoice.status,
    )


@order_router.post("/{order_id}/payments", response_model=PaymentResponse)
def record_payment(
    order_id: UUID,
    body: PaymentCreate,
    session: Session = Depends(get_session),
):
    """Step 4: Customer pays the invoice."""
    svc = OrderService(session)
    try:
        payment = svc.record_payment(
            order_id=order_id,
            amount=body.amount,
            currency=body.currency,
            method=body.method,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CircuitBreakerError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not payment:
        raise HTTPException(status_code=404, detail="Order not found")
    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        amount=payment.amount,
        currency=payment.currency,
        method=payment.method,
        status=payment.status,
        timestamp=payment.timestamp,
    )


@order_router.post("/payments/{payment_id}/verify", response_model=PaymentResponse)
def verify_payment(
    payment_id: UUID,
    body: PaymentVerification,
    session: Session = Depends(get_session),
):
    """Step 5: Accountant verifies a payment."""
    svc = OrderService(session)
    try:
        payment = svc.verify_payment(payment_id, verified=body.verified)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CircuitBreakerError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        amount=payment.amount,
        currency=payment.currency,
        method=payment.method,
        status=payment.status,
        timestamp=payment.timestamp,
    )


@order_router.patch("/{order_id}/ship", response_model=OrderResponse)
def ship_order(order_id: UUID, session: Session = Depends(get_session)):
    """Step 6: Order Staff ships a paid order."""
    svc = OrderService(session)
    try:
        order = svc.ship_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CircuitBreakerError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_response(order)


@order_router.patch("/{order_id}/close", response_model=OrderResponse)
def close_order(order_id: UUID, session: Session = Depends(get_session)):
    """Step 7: Order Staff closes a completed order."""
    svc = OrderService(session)
    try:
        order = svc.close_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_response(order)


@order_router.patch("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: UUID, session: Session = Depends(get_session)):
    """Cancel a pending or accepted order."""
    svc = OrderService(session)
    try:
        order = svc.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_response(order)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _order_to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
        invoice_id=order.invoice_id,
        payment_id=order.payment_id,
        total_amount=order.total_amount,
        line_items=[
            LineItemResponse(
                id=li.id,
                product_id=li.product_id,
                quantity=li.quantity,
                unit_price=li.unit_price,
                currency=li.currency,
                total=li.total,
            )
            for li in order.line_items
        ],
    )
