from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app import __version__
from app.api.routes import customers, invoices, orders, payments, products, system
from app.core.config import get_settings
from app.core.errors import install_exception_handlers
from app.core.observability import configure_observability
from app.core.openapi import configure_openapi
from app.db.models import CustomerModel, InvoiceModel, OrderModel, PaymentModel, ProductModel
from app.db.session import create_engine, create_session_factory
from app.domain.mappers import (
    serialize_customer_snapshot,
    serialize_invoice_snapshot,
    serialize_order_snapshot,
    serialize_payment_snapshot,
    serialize_product_snapshot,
)
from app.infrastructure.cache import EntityCache
from app.workers.outbox import OutboxDispatcher
from app.workers.state_sync import EntitySyncSpec, StateSynchronizer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    cache = EntityCache(
        redis,
        ttl_seconds=settings.cache_ttl_seconds,
        timeout_seconds=settings.dependency_timeout_seconds,
    )
    dispatcher = OutboxDispatcher(
        session_factory,
        redis,
        stream_name=settings.event_stream,
        max_rate=settings.event_max_rate,
        batch_size=settings.event_batch_size,
        poll_interval_seconds=settings.event_poll_interval_seconds,
        dependency_timeout_seconds=settings.dependency_timeout_seconds,
    )
    synchronizer = StateSynchronizer(
        session_factory,
        cache,
        (
            EntitySyncSpec("customer", CustomerModel, serialize_customer_snapshot),
            EntitySyncSpec("product", ProductModel, serialize_product_snapshot),
            EntitySyncSpec("order", OrderModel, serialize_order_snapshot),
            EntitySyncSpec("invoice", InvoiceModel, serialize_invoice_snapshot),
            EntitySyncSpec("payment", PaymentModel, serialize_payment_snapshot),
        ),
        interval_seconds=settings.state_sync_interval_seconds,
        dependency_timeout_seconds=settings.dependency_timeout_seconds,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.redis = redis
    app.state.cache = cache
    app.state.outbox_dispatcher = dispatcher
    app.state.state_synchronizer = synchronizer

    stop_event = asyncio.Event()
    tasks = [
        asyncio.create_task(dispatcher.run_forever(stop_event), name="outbox-dispatcher"),
        asyncio.create_task(synchronizer.run_forever(stop_event), name="state-synchronizer"),
    ]
    try:
        yield
    finally:
        stop_event.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Order Management System API",
        version=__version__,
        description="Backend-only OMS for ordering, invoicing, payment, shipping, and closure.",
        lifespan=lifespan,
    )
    configure_observability(application, settings.log_level)
    install_exception_handlers(application)
    configure_openapi(application)
    application.include_router(system.router)
    application.include_router(customers.router, prefix="/api/v1")
    application.include_router(products.router, prefix="/api/v1")
    application.include_router(orders.router, prefix="/api/v1")
    application.include_router(invoices.router, prefix="/api/v1")
    application.include_router(payments.router, prefix="/api/v1")

    @application.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {"service": settings.service_name, "version": __version__, "status": "ok"}

    return application


app = create_app()
