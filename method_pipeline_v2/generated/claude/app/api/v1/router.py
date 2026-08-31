"""Versioned API surface. Every route below is mounted under /api/v1."""
from fastapi import APIRouter

from app.api.v1 import customers, invoices, orders, payments, products

api_router = APIRouter()
api_router.include_router(customers.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
api_router.include_router(invoices.router)
api_router.include_router(payments.router)
