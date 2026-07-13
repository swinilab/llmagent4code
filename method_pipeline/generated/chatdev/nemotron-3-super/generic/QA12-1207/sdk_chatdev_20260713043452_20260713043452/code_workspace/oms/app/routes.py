from fastapi import APIRouter
from app.controllers import router as customers_router
from app.controllers_products import router as products_router
from app.controllers_orders import router as orders_router
from app.controllers_invoices import router as invoices_router
from app.controllers_payments import router as payments_router

api_router = APIRouter()

api_router.include_router(customers_router, prefix="", tags=["customers"])
api_router.include_router(products_router, prefix="", tags=["products"])
api_router.include_router(orders_router, prefix="", tags=["orders"])
api_router.include_router(invoices_router, prefix="", tags=["invoices"])
api_router.include_router(payments_router, prefix="", tags=["payments"])