"""
Product controller — REST endpoint handlers for product operations.

Includes search with keyword/price filtering (NFR 1.1 core journey).
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from oms.schemas.product import ProductCreate, ProductUpdate, ProductRead
from oms.schemas.common import PaginatedResponse
from oms.services.product import ProductService


class ProductController:
    """Handles product CRUD and search endpoints."""

    async def create_product(self, data: ProductCreate, session: AsyncSession) -> ProductRead:
        service = ProductService(session)
        product = await service.create_product(data)
        return ProductRead.model_validate(product)

    async def get_product(self, product_id: str, session: AsyncSession) -> ProductRead:
        service = ProductService(session)
        product = await service.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return ProductRead.model_validate(product)

    async def list_products(self, session: AsyncSession, page: int = 1, page_size: int = 20) -> PaginatedResponse[ProductRead]:
        service = ProductService(session)
        items, total = await service.list_products(page=page, page_size=page_size)
        return PaginatedResponse[ProductRead].create(
            items=[ProductRead.model_validate(p) for p in items],
            total=total, page=page, page_size=page_size,
        )

    async def search_products(
        self, session: AsyncSession,
        q: str | None = None, min_price: float | None = None,
        max_price: float | None = None, currency: str | None = None,
        page: int = 1, page_size: int = 20,
    ) -> PaginatedResponse[ProductRead]:
        service = ProductService(session)
        items, total = await service.search_products(
            query=q, min_price=min_price, max_price=max_price,
            currency=currency, page=page, page_size=page_size,
        )
        return PaginatedResponse[ProductRead].create(
            items=[ProductRead.model_validate(p) for p in items],
            total=total, page=page, page_size=page_size,
        )

    async def update_product(self, product_id: str, data: ProductUpdate, session: AsyncSession) -> ProductRead:
        service = ProductService(session)
        product = await service.update_product(product_id, data)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return ProductRead.model_validate(product)

    async def delete_product(self, product_id: str, session: AsyncSession) -> dict:
        service = ProductService(session)
        deleted = await service.delete_product(product_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return {"deleted": True, "id": product_id}


product_controller = ProductController()