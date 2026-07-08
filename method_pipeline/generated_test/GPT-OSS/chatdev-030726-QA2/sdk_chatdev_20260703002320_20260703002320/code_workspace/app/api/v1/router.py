"""
Versioned API router (v1).
"""

from fastapi import APIRouter
from app.controllers.customer_controller import router as customer_router
from app.controllers.product_controller import router as product_router
from app.controllers.order_controller import router as order_router
from app.controllers.payment_controller import router as payment_router
from app.controllers.invoice_controller import router as invoice_router
from app.controllers.config_controller import router as config_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(customer_router)
api_router.include_router(product_router)
api_router.include_router(order_router)
api_router.include_router(payment_router)
api_router.include_router(invoice_router)
api_router.include_router(config_router)
