"""Shared API dependencies.

`parse_entity_id` exists because FastAPI's built-in ``UUID`` path converter
answers 422 for a malformed id, while the Field Constraint Table (Implementation
note 2a) and the TC_*_ID_* test cases require **400**.
"""
import uuid
from typing import Annotated

from fastapi import Depends, Path, Request

from app.core.errors import ValidationError
from app.infra.cache import EntityCache
from app.services.services import (
    CustomerService,
    InvoiceService,
    OrderService,
    PaymentService,
    ProductService,
)


def parse_entity_id(entity_id: Annotated[str, Path(alias="entity_id")]) -> uuid.UUID:
    """400 on malformed; the service layer then answers 404 on non-existent."""
    raw = entity_id.strip()
    if len(raw) != 36:
        raise ValidationError("malformed id: expected a 36-character UUID")
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValidationError("malformed id: not a valid UUID") from exc


EntityId = Annotated[uuid.UUID, Depends(parse_entity_id)]


def get_cache(request: Request) -> EntityCache:
    return request.app.state.cache


def get_customer_service(cache: Annotated[EntityCache, Depends(get_cache)]) -> CustomerService:
    return CustomerService(cache)


def get_product_service(cache: Annotated[EntityCache, Depends(get_cache)]) -> ProductService:
    return ProductService(cache)


def get_order_service(cache: Annotated[EntityCache, Depends(get_cache)]) -> OrderService:
    return OrderService(cache)


def get_invoice_service(cache: Annotated[EntityCache, Depends(get_cache)]) -> InvoiceService:
    return InvoiceService(cache)


def get_payment_service(cache: Annotated[EntityCache, Depends(get_cache)]) -> PaymentService:
    return PaymentService(cache)
