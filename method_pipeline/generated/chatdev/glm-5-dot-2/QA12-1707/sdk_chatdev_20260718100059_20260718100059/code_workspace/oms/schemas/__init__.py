"""
Pydantic schemas (shared domain models).

These schemas serve as the contract between the backend API and any
frontend or external consumer. They are used for request validation,
response serialisation, and OpenAPI generation.
"""
from oms.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerRead, CustomerWithOrders,
)
from oms.schemas.product import ProductCreate, ProductUpdate, ProductRead
from oms.schemas.order import (
    OrderLineItemCreate, OrderLineItemRead, OrderCreate, OrderUpdate,
    OrderRead, OrderStatusUpdate,
)
from oms.schemas.payment import PaymentCreate, PaymentRead, PaymentVerify
from oms.schemas.invoice import (
    InvoiceCreate, InvoiceRead, InvoiceStatusUpdate,
)
from oms.schemas.common import PaginationParams, PaginatedResponse

__all__ = [
    "CustomerCreate", "CustomerUpdate", "CustomerRead", "CustomerWithOrders",
    "ProductCreate", "ProductUpdate", "ProductRead",
    "OrderLineItemCreate", "OrderLineItemRead", "OrderCreate", "OrderUpdate",
    "OrderRead", "OrderStatusUpdate",
    "PaymentCreate", "PaymentRead", "PaymentVerify",
    "InvoiceCreate", "InvoiceRead", "InvoiceStatusUpdate",
    "PaginationParams", "PaginatedResponse",
]