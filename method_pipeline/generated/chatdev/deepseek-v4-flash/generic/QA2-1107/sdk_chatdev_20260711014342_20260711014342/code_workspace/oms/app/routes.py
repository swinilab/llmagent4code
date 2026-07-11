"""
Route registration - aggregates all routers into the main app.
"""
from fastapi import FastAPI

from app.controllers import customer_router, order_router, product_router


def register_routes(app: FastAPI) -> None:
    """Attach all API routers to the FastAPI application."""
    app.include_router(customer_router)
    app.include_router(product_router)
    app.include_router(order_router)
