from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import asyncio
from typing import Dict, Any

from src.models import Customer, Product, Order, Payment, Invoice
from src.repositories import (
    CustomerRepository,
    ProductRepository,
    OrderRepository,
    PaymentRepository,
    InvoiceRepository,
)
from src.services import (
    RateLimiter,
    CustomerService,
    ProductService,
    OrderService,
    InvoiceService,
    PaymentService,
)


# Global services initialized at startup
services: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    # Initialize repositories
    customer_repo = CustomerRepository()
    product_repo = ProductRepository()
    order_repo = OrderRepository()
    payment_repo = PaymentRepository()
    invoice_repo = InvoiceRepository()
    
    # Initialize rate limiter (NFR 1.1)
    rate_limiter = RateLimiter(max_events=100, window_seconds=60)
    
    # Initialize services
    services["customer_service"] = CustomerService(customer_repo, rate_limiter)
    services["product_service"] = ProductService(product_repo, rate_limiter)
    services["order_service"] = OrderService(order_repo, customer_repo, product_repo, rate_limiter)
    services["invoice_service"] = InvoiceService(invoice_repo, order_repo, customer_repo, rate_limiter)
    services["payment_service"] = PaymentService(payment_repo, order_repo, invoice_repo, rate_limiter)
    
    yield
    
    # Cleanup on shutdown
    pass


app = FastAPI(
    title="Order Management System (OMS)",
    description="Production-grade backend-only e-commerce Order Management System",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for validation errors
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


# Exception handler for not found errors
@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": f"Resource not found: {exc}"}
    )


# Middleware for timeout detection (NFR 2.1)
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    timeout_seconds = 30  # Configurable timeout
    try:
        start_time = time.time()
        response = await asyncio.wait_for(call_next(request), timeout=timeout_seconds)
        elapsed = time.time() - start_time
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
        return response
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"detail": "Request timeout exceeded"}
        )


# Customer endpoints
@app.post("/api/v1/customers", status_code=status.HTTP_201_CREATED, tags=["Customer"])
async def create_customer(customer: Customer):
    """Create a new customer."""
    try:
        service = services["customer_service"]
        created = service.create_customer(customer)
        return created
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/customers/{customer_id}", tags=["Customer"])
async def get_customer(customer_id: str):
    """Get customer by ID."""
    service = services["customer_service"]
    customer = service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@app.get("/api/v1/customers", tags=["Customer"])
async def get_all_customers():
    """Get all customers."""
    service = services["customer_service"]
    return service.get_all_customers()


# Product endpoints
@app.post("/api/v1/products", status_code=status.HTTP_201_CREATED, tags=["Product"])
async def create_product(product: Product):
    """Create a new product."""
    try:
        service = services["product_service"]
        created = service.create_product(product)
        return created
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/products/{product_id}", tags=["Product"])
async def get_product(product_id: str):
    """Get product by ID."""
    service = services["product_service"]
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@app.get("/api/v1/products", tags=["Product"])
async def get_all_products():
    """Get all products."""
    service = services["product_service"]
    return service.get_all_products()


# Order endpoints
@app.post("/api/v1/orders", status_code=status.HTTP_201_CREATED, tags=["Order"])
async def create_order(order: Order):
    """Create a new order."""
    try:
        service = services["order_service"]
        created = service.create_order(order)
        return created
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/orders/{order_id}", tags=["Order"])
async def get_order(order_id: str):
    """Get order by ID."""
    service = services["order_service"]
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@app.get("/api/v1/orders", tags=["Order"])
async def get_all_orders():
    """Get all orders."""
    service = services["order_service"]
    return service.get_all_orders()


@app.post("/api/v1/orders/{order_id}/accept", tags=["Order Workflow"])
async def accept_order(order_id: str):
    """Accept an order (Order Staff action)."""
    service = services["order_service"]
    try:
        order = service.accept_order(order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@app.post("/api/v1/orders/{order_id}/ship", tags=["Order Workflow"])
async def ship_order(order_id: str):
    """Ship an order (Order Staff action)."""
    service = services["order_service"]
    try:
        order = service.ship_order(order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@app.post("/api/v1/orders/{order_id}/close", tags=["Order Workflow"])
async def close_order(order_id: str):
    """Close an order (Order Staff action)."""
    service = services["order_service"]
    try:
        order = service.close_order(order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@app.post("/api/v1/orders/{order_id}/cancel", tags=["Order Workflow"])
async def cancel_order(order_id: str):
    """Cancel an order."""
    service = services["order_service"]
    try:
        order = service.cancel_order(order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# Invoice endpoints
@app.post("/api/v1/invoices", status_code=status.HTTP_201_CREATED, tags=["Invoice"])
async def create_invoice(invoice: Invoice):
    """Create a new invoice (Accountant action)."""
    try:
        service = services["invoice_service"]
        created = service.create_invoice(invoice)
        return created
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/invoices/{invoice_id}", tags=["Invoice"])
async def get_invoice(invoice_id: str):
    """Get invoice by ID."""
    service = services["invoice_service"]
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@app.get("/api/v1/invoices", tags=["Invoice"])
async def get_all_invoices():
    """Get all invoices."""
    service = services["invoice_service"]
    return service.get_all_invoices()


@app.get("/api/v1/invoices/order/{order_id}", tags=["Invoice"])
async def get_invoice_by_order(order_id: str):
    """Get invoice by order reference."""
    service = services["invoice_service"]
    invoice = service.get_invoice_by_order_ref(order_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found for order")
    return invoice


# Payment endpoints
@app.post("/api/v1/payments", status_code=status.HTTP_201_CREATED, tags=["Payment"])
async def create_payment(payment: Payment):
    """Create a new payment (Customer action)."""
    try:
        service = services["payment_service"]
        created = service.create_payment(payment)
        return created
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/payments/{payment_id}", tags=["Payment"])
async def get_payment(payment_id: str):
    """Get payment by ID."""
    service = services["payment_service"]
    payment = service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@app.get("/api/v1/payments", tags=["Payment"])
async def get_all_payments():
    """Get all payments."""
    service = services["payment_service"]
    return service.get_all_payments()


@app.post("/api/v1/payments/{payment_id}/verify", tags=["Payment Workflow"])
async def verify_payment(payment_id: str):
    """Verify a payment (Accountant action)."""
    service = services["payment_service"]
    try:
        payment = service.verify_payment(payment_id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@app.post("/api/v1/payments/{payment_id}/reject", tags=["Payment Workflow"])
async def reject_payment(payment_id: str):
    """Reject a payment (Accountant action)."""
    service = services["payment_service"]
    try:
        payment = service.reject_payment(payment_id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


# Rate limit status endpoint (for monitoring NFR 1.1)
@app.get("/rate-limit-status", tags=["System"])
async def rate_limit_status():
    """Get current rate limiter status."""
    rate_limiter = services.get("customer_service", {}).rate_limiter if "customer_service" in services else None
    if rate_limiter:
        return {
            "max_events": rate_limiter.max_events,
            "window_seconds": rate_limiter.window_seconds,
            "current_events": len(rate_limiter._events)
        }
    return {"status": "rate_limiter_not_initialized"}
