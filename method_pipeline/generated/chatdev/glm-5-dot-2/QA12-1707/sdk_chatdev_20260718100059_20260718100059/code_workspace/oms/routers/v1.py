"""
API v1 router — aggregates all entity routers under /api/v1.

Provides a clean, versioned API surface that is OpenAPI-friendly.
"""
from fastapi import APIRouter

from oms.routers.customer import router as customer_router
from oms.routers.product import router as product_router
from oms.routers.order import router as order_router
from oms.routers.payment import router as payment_router
from oms.routers.invoice import router as invoice_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(customer_router, tags=["customers"])
v1_router.include_router(product_router, tags=["products"])
v1_router.include_router(order_router, tags=["orders"])
v1_router.include_router(payment_router, tags=["payments"])
v1_router.include_router(invoice_router, tags=["invoices"])