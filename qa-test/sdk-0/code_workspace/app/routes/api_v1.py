"""API version 1 router aggregation"""
from fastapi import APIRouter
from app.routers import order_router, product_router, payment_router, invoice_router

router = APIRouter()
router.include_router(order_router.router, prefix="/orders", tags=["orders"])
router.include_router(product_router.router, prefix="/products", tags=["products"])
router.include_router(payment_router.router, prefix="/payments", tags=["payments"])
router.include_router(invoice_router.router, prefix="/invoices", tags=["invoices"])
