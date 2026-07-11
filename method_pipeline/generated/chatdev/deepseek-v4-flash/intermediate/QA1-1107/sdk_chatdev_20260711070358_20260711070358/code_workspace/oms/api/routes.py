"""
FastAPI route definitions (controllers).
Implements REST endpoints with rate limiting, caching, and error handling.
"""
import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from oms.api.schemas import (
    CustomerCreate,
    CustomerResponse,
    ProductCreate,
    ProductResponse,
    OrderCreate,
    OrderResponse,
    OrderLineItemResponse,
    TransitionRequest,
    PaymentCreate,
    PaymentResponse,
    InvoiceCreate,
    InvoiceResponse,
    PaymentVerificationRequest,
    ErrorResponse,
)
from oms.application.services import (
    CustomerService,
    ProductService,
    OrderService,
    PaymentService,
    InvoiceService,
)
from oms.application.workflows import WorkflowService
from oms.adapters.repositories import (
    CustomerRepository,
    ProductRepository,
    OrderRepository,
    PaymentRepository,
    InvoiceRepository,
)
from oms.infrastructure.database import get_db_session
from oms.infrastructure.cache import Cache, get_cache
from oms.infrastructure.rate_limiter import TokenBucketRateLimiter, get_rate_limiter
from oms.infrastructure.task_queue import TaskQueue, get_task_queue
from oms.infrastructure.context import correlation_id_var
from oms.domain.errors import (
    DomainError,
    EntityNotFoundError,
    InvalidStateTransitionError,
    BusinessRuleViolationError,
    ConcurrencyConflictError,
)
from oms.domain.enums import OrderStatus, PaymentMethod
from oms.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1")


# --- Domain error handler (registered on app in main.py) ---

async def domain_error_handler(request: Request, exc: DomainError):
    status_map = {
        "ENTITY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVALID_STATE_TRANSITION": status.HTTP_409_CONFLICT,
        "BUSINESS_RULE_VIOLATION": status.HTTP_400_BAD_REQUEST,
        "CONCURRENCY_CONFLICT": status.HTTP_409_CONFLICT,
    }
    http_status = status_map.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=http_status,
        content={"detail": exc.message, "code": exc.code},
    )


# --- Dependency factories ---

def get_customer_service() -> CustomerService:
    return CustomerService(CustomerRepository())


def get_product_service(cache: Cache = Depends(get_cache)) -> ProductService:
    return ProductService(ProductRepository(), cache)


def get_order_service() -> OrderService:
    return OrderService(OrderRepository())


def get_payment_service() -> PaymentService:
    return PaymentService(PaymentRepository())


def get_invoice_service() -> InvoiceService:
    return InvoiceService(InvoiceRepository())


def get_workflow_service(
    customer_service: CustomerService = Depends(get_customer_service),
    product_service: ProductService = Depends(get_product_service),
    order_service: OrderService = Depends(get_order_service),
    payment_service: PaymentService = Depends(get_payment_service),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    task_queue: TaskQueue = Depends(get_task_queue),
) -> WorkflowService:
    return WorkflowService(
        customer_service=customer_service,
        product_service=product_service,
        order_service=order_service,
        payment_service=payment_service,
        invoice_service=invoice_service,
        task_queue=task_queue,
    )


# --- Rate limiting middleware ---

async def check_rate_limit(
    request: Request,
    rate_limiter: TokenBucketRateLimiter = Depends(get_rate_limiter),
):
    """Middleware to enforce rate limiting on critical paths."""
    if request.method == "POST":
        allowed = await rate_limiter.acquire()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry after 1 second.",
                headers={"Retry-After": "1"},
            )


# --- Correlation ID middleware ---

async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    token = correlation_id_var.set(correlation_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        correlation_id_var.reset(token)

# ===================== Customer Endpoints =====================

@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
)
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db_session),
    service: CustomerService = Depends(get_customer_service),
):
    customer = await service.create_customer(
        session, data.name, data.address, data.phone, data.banking_details, data.role
    )
    return customer


@router.get(
    "/customers",
    response_model=List[CustomerResponse],
    summary="List all customers",
)
async def list_customers(
    session: AsyncSession = Depends(get_db_session),
    service: CustomerService = Depends(get_customer_service),
):
    return await service.list_customers(session)


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer by ID",
)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_db_session),
    service: CustomerService = Depends(get_customer_service),
):
    return await service.get_customer(session, customer_id)


# ===================== Product Endpoints =====================

@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
    service: ProductService = Depends(get_product_service),
):
    product = await service.create_product(
        session, data.description, data.base_price, data.currency, data.stock_available
    )
    return product


@router.get(
    "/products",
    response_model=List[ProductResponse],
    summary="Search/browse products (cached, latency-sensitive)",
)
async def search_products(
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    service: ProductService = Depends(get_product_service),
):
    """Search products by description. Results are cached for fast reads."""
    return await service.search_products(session, q, limit, offset)


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID (cached)",
)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_db_session),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_product(session, product_id)


# ===================== Order Endpoints =====================

@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order (checkout path - rate limited)",
    dependencies=[Depends(check_rate_limit)],
)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    """Place a new order. This is on the critical checkout path (NFR 1.1)."""
    order = await workflow.place_order(
        session, data.customer_id,
        [item.model_dump() for item in data.line_items],
    )
    return order


@router.get(
    "/orders",
    response_model=List[OrderResponse],
    summary="List all orders",
)
async def list_orders(
    session: AsyncSession = Depends(get_db_session),
    service: OrderService = Depends(get_order_service),
):
    return await service.list_orders(session)


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
    service: OrderService = Depends(get_order_service),
):
    return await service.get_order(session, order_id)


@router.get(
    "/customers/{customer_id}/orders",
    response_model=List[OrderResponse],
    summary="List orders for a customer",
)
async def list_customer_orders(
    customer_id: str,
    session: AsyncSession = Depends(get_db_session),
    service: OrderService = Depends(get_order_service),
):
    return await service.list_customer_orders(session, customer_id)


@router.post(
    "/orders/{order_id}/transition",
    response_model=OrderResponse,
    summary="Transition order status (back-office)",
)
async def transition_order(
    order_id: str,
    data: TransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    """Transition an order to a new status. Used by back-office staff."""
    target = OrderStatus(data.target_status)
    return await workflow.transition_order(
        session, order_id, target, data.expected_version
    )


# ===================== Workflow Endpoints =====================

@router.post(
    "/orders/{order_id}/accept",
    response_model=OrderResponse,
    summary="Step 2: Order Staff accepts order",
)
async def accept_order(
    order_id: str,
    data: TransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.accept_order(session, order_id, data.expected_version)


@router.post(
    "/orders/{order_id}/invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 3: Accountant creates invoice",
)
async def create_invoice(
    order_id: str,
    data: InvoiceCreate,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.create_invoice_for_order(
        session, order_id, data.expected_version, data.billing_name, data.billing_address
    )


@router.post(
    "/orders/{order_id}/pay",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 4: Customer pays invoice (checkout path - rate limited)",
    dependencies=[Depends(check_rate_limit)],
)
async def pay_order(
    order_id: str,
    data: PaymentCreate,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    """Pay for an order. This is on the critical checkout path (NFR 1.1)."""
    return await workflow.pay_invoice(
        session, order_id, data.amount, data.currency,
        PaymentMethod(data.method),
    )


@router.post(
    "/orders/{order_id}/verify-payment",
    response_model=OrderResponse,
    summary="Step 5: Accountant verifies payment",
)
async def verify_payment(
    order_id: str,
    data: PaymentVerificationRequest,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.verify_payment(
        session, data.payment_id, order_id, data.expected_version
    )


@router.post(
    "/orders/{order_id}/ship",
    response_model=OrderResponse,
    summary="Step 6: Order Staff ships order",
)
async def ship_order(
    order_id: str,
    data: TransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.ship_order(session, order_id, data.expected_version)


@router.post(
    "/orders/{order_id}/close",
    response_model=OrderResponse,
    summary="Step 7: Order Staff closes order",
)
async def close_order(
    order_id: str,
    data: TransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.close_order(session, order_id, data.expected_version)


@router.post(
    "/orders/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancel an order (from any pre-SHIPPED state)",
)
async def cancel_order(
    order_id: str,
    data: TransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    return await workflow.cancel_order(session, order_id, data.expected_version)


# ===================== Payment Endpoints =====================

@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment by ID",
)
async def get_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_db_session),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.get_payment(session, payment_id)


# ===================== Invoice Endpoints =====================

@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice by ID",
)
async def get_invoice(
    invoice_id: str,
    session: AsyncSession = Depends(get_db_session),
    service: InvoiceService = Depends(get_invoice_service),
):
    return await service.get_invoice(session, invoice_id)


# ===================== Seed Data Endpoint =====================

@router.post(
    "/seed",
    summary="Seed test data for load testing (debug mode only)",
    status_code=status.HTTP_201_CREATED,
)
async def seed_test_data():
    """Seed the database with test customers and products for load testing."""
    from oms.load_test.seed_data import seed_test_data as do_seed
    result = await do_seed(num_customers=1000, num_products=100)
    return result


# ===================== Health & Metrics =====================

@router.get(
    "/health",
    summary="Health check endpoint",
)
async def health_check():
    return {"status": "healthy", "service": "oms"}


@router.get(
    "/metrics",
    summary="Runtime metrics for performance monitoring",
)
async def metrics(
    rate_limiter: TokenBucketRateLimiter = Depends(get_rate_limiter),
):
    """Expose runtime metrics for load testing and monitoring."""
    return {
        "rate_limiter": {
            "capacity": rate_limiter.capacity,
            "available_tokens": await rate_limiter.get_available_tokens(),
        },
        "version": "1.0.0",
    }
