"""
Product service: handles product catalog management.

Criticality: CORE (NFR 2.1) — product lookup is needed for order creation.
Recovery: Retry on transient DB errors (NFR 2.2).
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repositories import ProductRepository
from app.domain.models import Product
from app.domain.schemas import ProductCreate

logger = logging.getLogger(__name__)


class ProductService:
    """Encapsulates product business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_repo = ProductRepository(session)

    async def create_product(self, data: ProductCreate) -> Product:
        product = Product(
            description=data.description,
            base_price=data.base_price,
            currency=data.currency,
            available=data.available,
        )
        product = await self._product_repo.create(product)
        logger.info("Product %s created: %s", product.id, product.description)
        return product

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        return await self._product_repo.get(product_id)

    async def list_available_products(self) -> list[Product]:
        return list(await self._product_repo.list_available())
