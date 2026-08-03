"""Product service - the maintained-copy read path (ASR-P1, ASR-A3).

Scope decision (see architecture/ADRs.md): Product is read-mostly reference data
whose state does not advance through the seven-step workflow, so it is the entity
served from a maintained copy. Order, Payment, and Invoice are deliberately
excluded - a stale copy of those would make workflow state and transaction
rollbacks externally observable as incorrect, which ASR-A4 explicitly forbids.

The cache component itself (app.core.cache.TtlCache) is entity-agnostic; this
module supplies the loader and the key policy.
"""

from __future__ import annotations

import uuid
from typing import Optional

from app.core.cache import TtlCache
from app.core.config import settings
from app.core.errors import NotFoundError
from app.persistence.database import run_with_resilience, session_scope
from app.persistence.repositories import ProductRepository
from app.schemas.dto import ProductResponse, product_to_response

# Maintained copies hold fully-rendered response DTOs so that a cache hit does
# no ORM work and releases its admitted slot promptly - a slow hit would turn a
# read workload into an overload condition (see ASR-P1's interaction note).
product_cache: TtlCache[ProductResponse] = TtlCache(
    ttl_seconds=float(settings.cache_ttl_seconds), name="product"
)


def _cache_key(product_id: uuid.UUID) -> str:
    return f"product:{product_id}"


def _load_product(product_id: uuid.UUID) -> ProductResponse:
    """Refill a maintained copy from PostgreSQL under the resilience policy."""

    def operation() -> Optional[ProductResponse]:
        with session_scope() as session:
            product = ProductRepository(session).get(product_id)
            return None if product is None else product_to_response(product)

    result = run_with_resilience(operation, operation_name="product.get")
    if result is None:
        raise NotFoundError(f"Product {product_id} was not found")
    return result


def get_product(product_id: uuid.UUID) -> ProductResponse:
    """Serve a Product read, preferring the maintained copy.

    A miss populates through single-flight refill; during a database outage the
    cache serves a retained stale copy rather than failing, which is the degraded
    read ASR-A3 requires. A Product never read before has no copy to degrade to,
    so its read correctly surfaces DEPENDENCY_UNAVAILABLE.
    """
    return product_cache.get_or_load(_cache_key(product_id), lambda: _load_product(product_id))


def search_products(query: Optional[str]) -> list[ProductResponse]:
    """Search is not cached: the result set varies per query text.

    It still passes through the same resilience policy and the same admission
    control as every other business endpoint.
    """

    def operation() -> list[ProductResponse]:
        with session_scope() as session:
            products = ProductRepository(session).search(query)
            return [product_to_response(product) for product in products]

    return run_with_resilience(operation, operation_name="product.search")


def create_product(description: str, amount, currency) -> ProductResponse:
    from app.persistence.models import Product

    def operation() -> ProductResponse:
        with session_scope() as session:
            product = Product(
                description=description,
                price_amount=amount,
                price_currency=currency.value,
            )
            ProductRepository(session).add(product)
            return product_to_response(product)

    # A create is a write whose effect may already have been applied at the
    # database, so it is never blindly re-executed (ASR-A2 retry safety rule).
    return run_with_resilience(operation, operation_name="product.create", retryable=False)
