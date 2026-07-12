"""
ProductService — business logic for product catalog.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.models.orm_models import Product
from oms_backend.repositories.entities import ProductRepository
from oms_backend.schemas.domain import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductRepository(session)

    async def create(self, data: ProductCreate) -> Product:
        return await self.repo.create(
            sku=data.sku,
            name=data.name,
            description=data.description,
            base_price=data.base_price,
            currency=data.currency,
            stock_qty=data.stock_qty,
            is_active=data.is_active,
        )

    async def get(self, id: uuid.UUID) -> Product | None:
        return await self.repo.get_active(id)

    async def get_by_sku(self, sku: str) -> Product | None:
        return await self.repo.get_by_sku(sku)

    async def search(self, query: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list[Product], int]:
        return await self.repo.search(query=query, page=page, page_size=page_size)

    async def update(self, id: uuid.UUID, data: ProductUpdate) -> Product | None:
        update_data: dict[str, Any] = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.base_price is not None:
            update_data["base_price"] = data.base_price
        if data.stock_qty is not None:
            update_data["stock_qty"] = data.stock_qty
        if data.is_active is not None:
            update_data["is_active"] = data.is_active
        if not update_data:
            return await self.repo.get_active(id)
        return await self.repo.update(id, **update_data)

    async def list_active(self, page: int = 1, page_size: int = 20) -> tuple[list[Product], int]:
        return await self.repo.list_all(page=page, page_size=page_size, filters={"is_active": True}, order_by="name")

    async def reserve_stock(self, product_id: uuid.UUID, quantity: int) -> bool:
        """Decrement stock atomically if sufficient. Returns True if reserved."""
        product = await self.repo.get_active(product_id)
        if not product or product.stock_qty < quantity:
            return False
        updated = await self.repo.update(product_id, stock_qty=product.stock_qty - quantity)
        return updated is not None

    async def restore_stock(self, product_id: uuid.UUID, quantity: int) -> bool:
        """Restore stock on order cancellation."""
        product = await self.repo.get_active(product_id)
        if not product:
            return False
        await self.repo.update(product_id, stock_qty=product.stock_qty + quantity)
        return True
