"""
Main application entry point for the OMS backend.
Assembles all components: database, repositories, services, controllers,
and infrastructure (queue, circuit breaker, degradation, state manager).
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.controllers.customer_controller import create_customer_router
from app.controllers.invoice_controller import create_invoice_router
from app.controllers.order_controller import create_order_router
from app.controllers.payment_controller import create_payment_router
from app.controllers.product_controller import create_product_router
from app.database import get_session, init_db
from app.infrastructure.graceful_degradation import GracefulDegradationManager
from app.infrastructure.health_check import create_health_router
from app.infrastructure.queue_manager import QueueManager
from app.infrastructure.state_manager import StateManager
from app.repositories.customer_repo import CustomerRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.product_repo import ProductRepository
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.product_service import ProductService

logger = logging.getLogger(__name__)

# ── Global infrastructure instances ──────────────────────────────────
queue_mgr = QueueManager()
degradation_mgr = GracefulDegradationManager()
state_mgr = StateManager()
startup_time = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("OMS Backend starting up ...")

    await init_db()
    logger.info("Database tables created")

    await queue_mgr.start(handler=queue_task_handler)
    await degradation_mgr.start()
    await state_mgr.start()

    logger.info("OMS Backend startup complete")
    yield

    logger.info("OMS Backend shutting down ...")
    await queue_mgr.stop()
    await degradation_mgr.stop()
    await state_mgr.stop()
    logger.info("OMS Backend shutdown complete")


async def queue_task_handler(task_type: str, payload: dict[str, Any]) -> None:
    """Handle tasks from the async queue — processes real order operations."""
    from app.database import async_session_factory
    from app.repositories.customer_repo import CustomerRepository
    from app.repositories.order_repo import OrderRepository
    from app.repositories.product_repo import ProductRepository
    from app.repositories.invoice_repo import InvoiceRepository
    from app.repositories.payment_repo import PaymentRepository
    from app.services.order_service import OrderService
    from app.services.invoice_service import InvoiceService
    from app.services.payment_service import PaymentService

    logger.info("Processing queued task: %s %s", task_type, payload)
    async with async_session_factory() as session:
        try:
            if task_type == "place_order":
                order_repo = OrderRepository(session)
                product_repo = ProductRepository(session)
                svc = OrderService(order_repo, product_repo, CustomerRepository(session))
                result = await svc.place_order(
                    customer_id=payload["customer_id"],
                    items=payload["items"],
                )
                logger.info("Order placed via queue: %s", result.id)

            elif task_type == "process_payment":
                payment_repo = PaymentRepository(session)
                order_repo = OrderRepository(session)
                invoice_repo = InvoiceRepository(session)
                svc = PaymentService(payment_repo, order_repo, invoice_repo)
                result = await svc.process_payment(
                    order_id=payload["order_id"],
                    amount=payload["amount"],
                    currency=payload.get("currency", "USD"),
                    method=payload["method"],
                )
                logger.info("Payment processed via queue: %s", result.id)

            elif task_type == "create_invoice":
                invoice_repo = InvoiceRepository(session)
                order_repo = OrderRepository(session)
                svc = InvoiceService(invoice_repo, order_repo)
                result = await svc.create_invoice(
                    order_id=payload["order_id"],
                    billing_info=payload["billing_info"],
                    due_days=payload.get("due_days", 30),
                )
                logger.info("Invoice created via queue: %s", result.id)

            else:
                logger.warning("Unknown task type: %s", task_type)

            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.exception("Queue task failed: %s %s", task_type, exc)


# ── Middleware: request ID ───────────────────────────────────────────
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for tracing."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Middleware: global error handler ─────────────────────────────────
async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a consistent JSON error."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request.headers.get("X-Request-ID", "")},
    )


# ── Dependency: per-request database session ─────────────────────────
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope per request (reuses database.get_session)."""
    async with get_session() as session:
        yield session


# ── Dependency: service instances ────────────────────────────────────
async def get_customer_service(
    session: AsyncSession = Depends(get_db_session),
) -> CustomerService:
    return CustomerService(CustomerRepository(session))


async def get_product_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProductService:
    return ProductService(ProductRepository(session))


async def get_order_service(
    session: AsyncSession = Depends(get_db_session),
) -> OrderService:
    return OrderService(
        OrderRepository(session),
        ProductRepository(session),
        CustomerRepository(session),
    )


async def get_payment_service(
    session: AsyncSession = Depends(get_db_session),
) -> PaymentService:
    return PaymentService(
        PaymentRepository(session),
        OrderRepository(session),
        InvoiceRepository(session),
    )


async def get_invoice_service(
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceService:
    return InvoiceService(InvoiceRepository(session), OrderRepository(session))


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Order Management System (OMS)",
        version="1.0.0",
        description="Production-grade e-commerce Order Management System backend.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(Exception, global_error_handler)

    # ── Register routers with dependency injection ────────────────────
    app.include_router(
        create_customer_router(dep_service=get_customer_service)
    )
    app.include_router(
        create_product_router(
            dep_service=get_product_service,
            degradation_mgr=degradation_mgr,
        )
    )
    app.include_router(
        create_order_router(
            dep_service=get_order_service,
            queue_mgr=queue_mgr,
        )
    )
    app.include_router(
        create_payment_router(
            dep_service=get_payment_service,
            queue_mgr=queue_mgr,
        )
    )
    app.include_router(
        create_invoice_router(
            dep_service=get_invoice_service,
            queue_mgr=queue_mgr,
        )
    )
    app.include_router(
        create_health_router(queue_mgr, degradation_mgr, state_mgr, startup_time)
    )

    return app


app = create_app()


def run() -> None:
    """Run the application server."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
    )


if __name__ == "__main__":
    run()
