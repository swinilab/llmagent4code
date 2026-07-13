from fastapi import APIRouter
from app.api.v1.endpoints import customer, order, product, payment, invoice

api_router = APIRouter()
api_router.include_router(customer.router, prefix="/customers", tags=["customers"])
api_router.include_router(order.router, prefix="/orders", tags=["orders"])
api_router.include_router(product.router, prefix="/products", tags=["products"])
api_router.include_router(payment.router, prefix="/payments", tags=["payments"])
api_router.include_router(invoice.router, prefix="/invoices", tags=["invoices"])