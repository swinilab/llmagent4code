from fastapi import APIRouter
from oms_backend.app.api.v1.endpoints import customer, product, order, invoice, payment

api_router = APIRouter()
api_router.include_router(customer.router, prefix="/customers", tags=["customers"])
api_router.include_router(product.router, prefix="/products", tags=["products"])
api_router.include_router(order.router, prefix="/orders", tags=["orders"])
api_router.include_router(invoice.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(payment.router, prefix="/payments", tags=["payments"])