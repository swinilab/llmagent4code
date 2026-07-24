"""
Product service — search and retrieval.
"""
from __future__ import annotations

from app.repositories.product_repo import ProductRepository
from app.schemas.product_schema import ProductResponse


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo

    async def search(
        self,
        query: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ProductResponse], int]:
        skip = (page - 1) * size
        products, total = await self._repo.search(query=query, skip=skip, limit=size)
        return [ProductResponse.model_validate(p) for p in products], total

    async def get_by_id(self, product_id: str) -> ProductResponse | None:
        product = await self._repo.get(product_id)
        if product is None:
            return None
        return ProductResponse.model_validate(product)

    async def create(
        self,
        name: str,
        description: str,
        base_price: float,
        currency: str,
        stock_quantity: int,
    ) -> ProductResponse:
        product = await self._repo.create(
            name=name,
            description=description,
            base_price=base_price,
            currency=currency,
            stock_quantity=stock_quantity,
        )
        return ProductResponse.model_validate(product)
