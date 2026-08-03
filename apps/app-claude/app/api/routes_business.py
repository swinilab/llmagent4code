"""Public business routes under /api/v1.

Handlers are thin: validation lives in the DTOs, and cross-cutting concerns
(admission control, timeout, retry, transactions, caching) live in their own
components. Service calls are synchronous, so each is dispatched to a worker
thread to keep the event loop free while a request holds its admitted slot.

Path parameters are typed `uuid.UUID`, so a malformed UUID is rejected with 400
before the handler runs, while a well-formed unknown UUID reaches the service and
yields 404.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query, Response, status
from starlette.concurrency import run_in_threadpool

from app.schemas.dto import (
    CustomerCreateRequest,
    CustomerResponse,
    ErrorResponse,
    InvoiceCreateRequest,
    InvoiceResponse,
    OrderCreateRequest,
    OrderResponse,
    PaymentCreateRequest,
    PaymentResponse,
    ProductCreateRequest,
    ProductResponse,
    ProductSearchResponse,
)
from app.services import customer_service, order_service, product_service

router = APIRouter(prefix="/api/v1")

# Response classes documented on every public operation. 429/503/504 are produced
# by the cross-cutting mechanisms rather than the handlers themselves.
COMMON_ERRORS: dict[int | str, dict] = {
    400: {"model": ErrorResponse, "description": "Malformed request or field-constraint violation"},
    429: {"model": ErrorResponse, "description": "Controlled overload rejection"},
    503: {"model": ErrorResponse, "description": "Dependency unavailable or degraded write"},
    504: {"model": ErrorResponse, "description": "Dependency timeout"},
}

READ_ERRORS: dict[int | str, dict] = {
    **COMMON_ERRORS,
    404: {"model": ErrorResponse, "description": "Valid identifier but resource not found"},
}

WORKFLOW_ERRORS: dict[int | str, dict] = {
    **READ_ERRORS,
    409: {"model": ErrorResponse, "description": "Invalid workflow state or illegal transition"},
}


# --------------------------------------------------------------------------
# Customers
# --------------------------------------------------------------------------


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createCustomer",
    summary="Create a customer",
    description=(
        "Creates a Customer synchronously and returns the created resource. "
        "`id` and `orderHistory` are server-derived and must not be supplied. "
        "`role` is fixed at creation and immutable thereafter."
    ),
    responses=COMMON_ERRORS,
    tags=["Customers"],
)
async def create_customer(payload: CustomerCreateRequest) -> CustomerResponse:
    return await run_in_threadpool(customer_service.create_customer, payload)


@router.get(
    "/customers/{id}",
    response_model=CustomerResponse,
    operation_id="getCustomer",
    summary="Retrieve a customer",
    description="Returns a Customer including its server-derived `orderHistory`.",
    responses=READ_ERRORS,
    tags=["Customers"],
)
async def get_customer(id: uuid.UUID) -> CustomerResponse:
    return await run_in_threadpool(customer_service.get_customer, id)


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createProduct",
    summary="Create a product",
    description=(
        "Creates a Product synchronously. `price.amount` must carry exactly two "
        "decimal places and is rejected rather than rounded."
    ),
    responses=COMMON_ERRORS,
    tags=["Products"],
)
async def create_product(payload: ProductCreateRequest) -> ProductResponse:
    return await run_in_threadpool(
        product_service.create_product,
        payload.description,
        payload.price.amount,
        payload.price.currency,
    )


@router.get(
    "/products",
    response_model=ProductSearchResponse,
    operation_id="searchProducts",
    summary="Search products",
    description=(
        "Searches Products by a case-insensitive substring of `description`. "
        "Passes through admission control like every public business endpoint."
    ),
    responses=COMMON_ERRORS,
    tags=["Products"],
)
async def search_products(
    query: Optional[str] = Query(default=None, description="Substring matched against description"),
) -> ProductSearchResponse:
    items = await run_in_threadpool(product_service.search_products, query)
    return ProductSearchResponse(items=items, count=len(items))


@router.get(
    "/products/{id}",
    response_model=ProductResponse,
    operation_id="getProduct",
    summary="Retrieve a product",
    description=(
        "Returns a Product, served from the maintained cached copy when one is "
        "fresh. During a database outage a previously warmed Product is still "
        "served from its retained copy; a never-read Product returns 503."
    ),
    responses=READ_ERRORS,
    tags=["Products"],
)
async def get_product(id: uuid.UUID) -> ProductResponse:
    return await run_in_threadpool(product_service.get_product, id)


# --------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createOrder",
    summary="Create an order (workflow step 1)",
    description=(
        "Creates an Order in status `PLACED`. `unitPriceSnapshot` and "
        "`totalAmount` are server-computed from current product prices. "
        "Duplicate `productRef` values are rejected with 400."
    ),
    responses=WORKFLOW_ERRORS,
    tags=["Orders"],
)
async def create_order(payload: OrderCreateRequest) -> OrderResponse:
    return await run_in_threadpool(order_service.create_order, payload)


@router.get(
    "/orders/{id}",
    response_model=OrderResponse,
    operation_id="getOrder",
    summary="Retrieve an order",
    description="Returns an Order with its line items and current workflow status.",
    responses=READ_ERRORS,
    tags=["Orders"],
)
async def get_order(id: uuid.UUID) -> OrderResponse:
    return await run_in_threadpool(order_service.get_order, id)


@router.post(
    "/orders/{id}/accept",
    response_model=OrderResponse,
    operation_id="acceptOrder",
    summary="Accept an order (workflow step 2)",
    description="Transitions `PLACED -> ACCEPTED`. Any other source state yields 409.",
    responses=WORKFLOW_ERRORS,
    tags=["Orders"],
)
async def accept_order(id: uuid.UUID) -> OrderResponse:
    return await run_in_threadpool(order_service.accept_order, id)


@router.post(
    "/orders/{id}/ship",
    response_model=OrderResponse,
    operation_id="shipOrder",
    summary="Ship an order (workflow step 6)",
    description="Transitions `VERIFIED -> SHIPPED`. Any other source state yields 409.",
    responses=WORKFLOW_ERRORS,
    tags=["Orders"],
)
async def ship_order(id: uuid.UUID) -> OrderResponse:
    return await run_in_threadpool(order_service.ship_order, id)


@router.post(
    "/orders/{id}/close",
    response_model=OrderResponse,
    operation_id="closeOrder",
    summary="Close an order (workflow step 7)",
    description="Transitions `SHIPPED -> CLOSED`. Any other source state yields 409.",
    responses=WORKFLOW_ERRORS,
    tags=["Orders"],
)
async def close_order(id: uuid.UUID) -> OrderResponse:
    return await run_in_threadpool(order_service.close_order, id)


# --------------------------------------------------------------------------
# Invoices
# --------------------------------------------------------------------------


@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createInvoice",
    summary="Create an invoice (workflow step 3)",
    description=(
        "Issues an Invoice for an `ACCEPTED` Order and advances that Order to "
        "`INVOICED`, setting `invoiceRef`. Both updates occur in one transaction. "
        "`issueDate` defaults to today and `dueDate` to issueDate + 7 days."
    ),
    responses=WORKFLOW_ERRORS,
    tags=["Invoices"],
)
async def create_invoice(payload: InvoiceCreateRequest) -> InvoiceResponse:
    return await run_in_threadpool(order_service.create_invoice, payload)


@router.get(
    "/invoices/{id}",
    response_model=InvoiceResponse,
    operation_id="getInvoice",
    summary="Retrieve an invoice",
    description="Returns an Invoice with its billing snapshot and dates in dd/MM/yyyy.",
    responses=READ_ERRORS,
    tags=["Invoices"],
)
async def get_invoice(id: uuid.UUID) -> InvoiceResponse:
    return await run_in_threadpool(order_service.get_invoice, id)


# --------------------------------------------------------------------------
# Payments
# --------------------------------------------------------------------------


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPayment",
    summary="Create a payment (workflow step 4)",
    description=(
        "Submits a Payment against an `INVOICED` Order. The amount must exactly "
        "equal the invoice total. The Payment starts `PENDING` while the Order "
        "advances to `PAID`; both updates occur in one transaction."
    ),
    responses=WORKFLOW_ERRORS,
    tags=["Payments"],
)
async def create_payment(payload: PaymentCreateRequest) -> PaymentResponse:
    return await run_in_threadpool(order_service.create_payment, payload)


@router.get(
    "/payments/{id}",
    response_model=PaymentResponse,
    operation_id="getPayment",
    summary="Retrieve a payment",
    description="Returns a Payment with its current verification status.",
    responses=READ_ERRORS,
    tags=["Payments"],
)
async def get_payment(id: uuid.UUID) -> PaymentResponse:
    return await run_in_threadpool(order_service.get_payment, id)


@router.post(
    "/payments/{id}/verify",
    response_model=PaymentResponse,
    operation_id="verifyPayment",
    summary="Verify a payment (workflow step 5)",
    description=(
        "Atomically marks the Payment `VERIFIED`, the Invoice `PAID`, and the "
        "Order `VERIFIED`. All three updates share one transaction, so a fault "
        "rolls back every one of them and returns `TRANSACTION_FAILED`."
    ),
    responses={
        **WORKFLOW_ERRORS,
        500: {"model": ErrorResponse, "description": "Transaction rolled back due to an internal fault"},
    },
    tags=["Payments"],
)
async def verify_payment(id: uuid.UUID) -> PaymentResponse:
    return await run_in_threadpool(order_service.verify_payment, id)
