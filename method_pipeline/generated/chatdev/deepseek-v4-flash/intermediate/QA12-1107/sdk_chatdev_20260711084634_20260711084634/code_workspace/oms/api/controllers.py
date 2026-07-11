"""
FastAPI route handlers (controllers) for the OMS.

All endpoints are versioned under /api/v1/.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, status

from oms.api.schemas import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
    InvoiceResponse,
    LineItemRequest,
    OrderCreateRequest,
    OrderPayRequest,
    OrderResponse,
    PaymentResponse,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from oms.domain.exceptions import (
    ConcurrencyConflictError,
    CustomerNotFoundError,
    DomainError,
    InsufficientStockError,
    InvalidPaymentMethodError,
    InvalidStateTransitionError,
    InvoiceNotFoundError,
    OrderNotFoundError,
    PaymentAmountMismatchError,
    PaymentNotFoundError,
    ProductNotFoundError,
)
from oms.services.customer_service import CustomerService
from oms.services.invoice_service import InvoiceService
from oms.services.order_service import OrderService
from oms.services.payment_service import PaymentService
from oms.services.product_service import ProductService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# Service instances
_customer_svc = CustomerService()
_product_svc = ProductService()
_order_svc = OrderService()
_payment_svc = PaymentService()
_invoice_svc = InvoiceService()


# ---------------------------------------------------------------------------
# Exception handler mapping
# ---------------------------------------------------------------------------

def _handle_domain_error(exc: DomainError) -> HTTPException:
    """Map domain exceptions to HTTP responses."""
    mapping: dict[type, tuple[int, str]] = {
        OrderNotFoundError: (status.HTTP_404_NOT_FOUND, "ORDER_NOT_FOUND"),
        ProductNotFoundError: (status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND"),
        CustomerNotFoundError: (status.HTTP_404_NOT_FOUND, "CUSTOMER_NOT_FOUND"),
        InvoiceNotFoundError: (status.HTTP_404_NOT_FOUND, "INVOICE_NOT_FOUND"),
        PaymentNotFoundError: (status.HTTP_404_NOT_FOUND, "PAYMENT_NOT_FOUND"),
        InvalidStateTransitionError: (
            status.HTTP_409_CONFLICT, "INVALID_STATE_TRANSITION"
        ),
        InsufficientStockError: (
            status.HTTP_422_UNPROCESSABLE_ENTITY, "INSUFFICIENT_STOCK"
        ),
        ConcurrencyConflictError: (
            status.HTTP_409_CONFLICT, "CONCURRENCY_CONFLICT"
        ),
        InvalidPaymentMethodError: (
            status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_PAYMENT_METHOD"
        ),
        PaymentAmountMismatchError: (
            status.HTTP_422_UNPROCESSABLE_ENTITY, "PAYMENT_AMOUNT_MISMATCH"
        ),
    }
    exc_type = type(exc)
    if exc_type in mapping:
        http_status, code = mapping[exc_type]
        return HTTPException(
            status_code=http_status,
            detail={"error_code": code, "message": str(exc)},
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"error_code": "INTERNAL_ERROR", "message": str(exc)},
    )


# ---------------------------------------------------------------------------
# Customer endpoints
# ---------------------------------------------------------------------------

@router.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_customer(body: CustomerCreateRequest) -> Any:
    """Create a new customer."""
    try:
        customer = await _customer_svc.create_customer(
            name=body.name,
            phone=body.phone,
            address=body.address.model_dump() if body.address else None,
            banking_details=body.banking_details.model_dump()
            if body.banking_details else None,
        )
        return CustomerResponse(
            id=customer.id,
            name=customer.name,
            phone=customer.phone,
            address=customer.address.__dict__ if customer.address else None,
            role=customer.role.value if hasattr(customer.role, "value") else customer.role,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            version=customer.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str) -> Any:
    """Get a customer by ID."""
    try:
        customer = await _customer_svc.get_customer(customer_id)
        return CustomerResponse(
            id=customer.id,
            name=customer.name,
            phone=customer.phone,
            address=customer.address.__dict__ if customer.address else None,
            role=customer.role.value if hasattr(customer.role, "value") else customer.role,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            version=customer.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(customer_id: str, body: CustomerUpdateRequest) -> Any:
    """Update a customer."""
    try:
        customer = await _customer_svc.update_customer(
            customer_id=customer_id,
            name=body.name,
            phone=body.phone,
            address=body.address.model_dump() if body.address else None,
        )
        return CustomerResponse(
            id=customer.id,
            name=customer.name,
            phone=customer.phone,
            address=customer.address.__dict__ if customer.address else None,
            role=customer.role.value if hasattr(customer.role, "value") else customer.role,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            version=customer.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


# ---------------------------------------------------------------------------
# Product endpoints
# ---------------------------------------------------------------------------

@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(body: ProductCreateRequest) -> Any:
    """Create a new product."""
    try:
        product = await _product_svc.create_product(
            name=body.name,
            description=body.description,
            price_amount=body.price_amount,
            price_currency=body.price_currency,
            stock=body.stock,
        )
        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            base_price_amount=str(product.base_price.amount),
            base_price_currency=product.base_price.currency,
            stock=product.stock,
            available=product.available,
            created_at=product.created_at,
            updated_at=product.updated_at,
            version=product.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.get("/products", response_model=list[ProductResponse])
async def list_products() -> Any:
    """List all available products."""
    products = await _product_svc.list_available_products()
    return [
        ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            base_price_amount=str(p.base_price.amount),
            base_price_currency=p.base_price.currency,
            stock=p.stock,
            available=p.available,
            created_at=p.created_at,
            updated_at=p.updated_at,
            version=p.version,
        )
        for p in products
    ]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str) -> Any:
    """Get a product by ID."""
    try:
        product = await _product_svc.get_product(product_id)
        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            base_price_amount=str(product.base_price.amount),
            base_price_currency=product.base_price.currency,
            stock=product.stock,
            available=product.available,
            created_at=product.created_at,
            updated_at=product.updated_at,
            version=product.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, body: ProductUpdateRequest) -> Any:
    """Update a product."""
    try:
        product = await _product_svc.update_product(
            product_id=product_id,
            name=body.name,
            description=body.description,
            price_amount=body.price_amount,
            price_currency=body.price_currency,
            stock=body.stock,
            available=body.available,
        )
        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            base_price_amount=str(product.base_price.amount),
            base_price_currency=product.base_price.currency,
            stock=product.stock,
            available=product.available,
            created_at=product.created_at,
            updated_at=product.updated_at,
            version=product.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------

@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(body: OrderCreateRequest) -> Any:
    """Place a new order (checkout — latency-critical path)."""
    try:
        order = await _order_svc.create_order(
            customer_id=body.customer_id,
            items=[item.model_dump() for item in body.items],
            shipping_address=body.shipping_address.model_dump()
            if body.shipping_address else None,
            notes=body.notes,
        )
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str) -> Any:
    """Get an order by ID."""
    try:
        order = await _order_svc.get_order(order_id)
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(
    customer_id: str | None = None,
    status: str | None = None,
) -> Any:
    """List orders, optionally filtered by customer or status."""
    try:
        if customer_id:
            orders = await _order_svc.get_orders_by_customer(customer_id)
        elif status:
            orders = await _order_svc.get_orders_by_status(status)
        else:
            orders = await _order_svc.get_orders_by_status("CREATED")
        return [
            OrderResponse(
                id=o.id,
                customer_id=o.customer_id,
                line_items=[li.__dict__ for li in o.line_items],
                status=o.status.value,
                total_amount=str(o.total_amount.amount),
                total_currency=o.total_amount.currency,
                invoice_ref=o.invoice_ref,
                payment_ref=o.payment_ref,
                shipping_address=o.shipping_address.__dict__
                if o.shipping_address else None,
                notes=o.notes,
                created_at=o.created_at,
                updated_at=o.updated_at,
                version=o.version,
            )
            for o in orders
        ]
    except DomainError as exc:
        raise _handle_domain_error(exc)


# ---------------------------------------------------------------------------
# Order workflow endpoints (role-based operations)
# ---------------------------------------------------------------------------

@router.post("/orders/{order_id}/accept", response_model=OrderResponse)
async def accept_order(order_id: str) -> Any:
    """Order Staff: accept an order (CREATED → ACCEPTED)."""
    try:
        order = await _order_svc.accept_order(order_id)
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.post("/orders/{order_id}/pay", response_model=OrderResponse)
async def pay_order(order_id: str, body: OrderPayRequest) -> Any:
    """Customer: pay for an order (INVOICED → PAID)."""
    try:
        order = await _order_svc.pay_order(
            order_id=order_id,
            amount=body.amount,
            currency=body.currency,
            method=body.method,
        )
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.post("/orders/{order_id}/verify-payment", response_model=OrderResponse)
async def verify_payment(order_id: str) -> Any:
    """Accountant: verify payment for an order."""
    try:
        order = await _order_svc.verify_payment(order_id)
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.post("/orders/{order_id}/ship", response_model=OrderResponse)
async def ship_order(order_id: str) -> Any:
    """Order Staff: ship a paid order (PAID → SHIPPED)."""
    try:
        order = await _order_svc.ship_order(order_id)
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.post("/orders/{order_id}/close", response_model=OrderResponse)
async def close_order(order_id: str) -> Any:
    """Order Staff: close a shipped order (SHIPPED → CLOSED)."""
    try:
        order = await _order_svc.close_order(order_id)
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: str) -> Any:
    """Cancel an order."""
    try:
        order = await _order_svc.cancel_order(order_id)
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            line_items=[li.__dict__ for li in order.line_items],
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            version=order.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


# ---------------------------------------------------------------------------
# Payment endpoints
# ---------------------------------------------------------------------------

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str) -> Any:
    """Get a payment by ID."""
    try:
        payment = await _payment_svc.get_payment(payment_id)
        return PaymentResponse(
            id=payment.id,
            order_id=payment.order_id,
            amount=str(payment.amount.amount),
            currency=payment.amount.currency,
            status=payment.status.value,
            method=payment.method.value,
            transaction_id=payment.transaction_id,
            paid_at=payment.paid_at,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            version=payment.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.get("/orders/{order_id}/payments", response_model=list[PaymentResponse])
async def get_order_payments(order_id: str) -> Any:
    """Get all payments for an order."""
    payments = await _payment_svc.get_payments_by_order(order_id)
    return [
        PaymentResponse(
            id=p.id,
            order_id=p.order_id,
            amount=str(p.amount.amount),
            currency=p.amount.currency,
            status=p.status.value,
            method=p.method.value,
            transaction_id=p.transaction_id,
            paid_at=p.paid_at,
            created_at=p.created_at,
            updated_at=p.updated_at,
            version=p.version,
        )
        for p in payments
    ]


# ---------------------------------------------------------------------------
# Invoice endpoints
# ---------------------------------------------------------------------------

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str) -> Any:
    """Get an invoice by ID."""
    try:
        invoice = await _invoice_svc.get_invoice(invoice_id)
        return InvoiceResponse(
            id=invoice.id,
            order_id=invoice.order_id,
            customer_id=invoice.customer_id,
            billing_address=invoice.billing_address.__dict__
            if invoice.billing_address else None,
            line_items=[li.__dict__ for li in invoice.line_items],
            subtotal=str(invoice.subtotal.amount),
            tax=str(invoice.tax.amount),
            total=str(invoice.total.amount),
            currency=invoice.subtotal.currency,
            status=invoice.status.value,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            version=invoice.version,
        )
    except DomainError as exc:
        raise _handle_domain_error(exc)


@router.get("/orders/{order_id}/invoices", response_model=list[InvoiceResponse])
async def get_order_invoices(order_id: str) -> Any:
    """Get all invoices for an order."""
    invoices = await _invoice_svc.get_invoices_by_order(order_id)
    return [
        InvoiceResponse(
            id=inv.id,
            order_id=inv.order_id,
            customer_id=inv.customer_id,
            billing_address=inv.billing_address.__dict__
            if inv.billing_address else None,
            line_items=[li.__dict__ for li in inv.line_items],
            subtotal=str(inv.subtotal.amount),
            tax=str(inv.tax.amount),
            total=str(inv.total.amount),
            currency=inv.subtotal.currency,
            status=inv.status.value,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            paid_at=inv.paid_at,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            version=inv.version,
        )
        for inv in invoices
    ]
