"""Product service: browse/search with cache-aside layer."""

from typing import Any, Optional
from uuid import UUID

from app.domain.models import Product
from app.repositories.product_repo import ProductRepository


class ProductService:
    """Handles product browse/search with cache-aside (Redis)."""

    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    async def get_product(self, product_id: UUID) -> Optional[Product]:
        """Get a product by ID (uses cache-aside)."""
        model = await self._product_repo.get_by_id_cached(product_id)
        if model is None:
            return None
        return self._model_to_domain(model)

    async def search_products(self, query: str, page: int = 1, page_size: int = 20) -> list[Product]:
        """Search products by name (uses cache-aside)."""
        models = await self._product_repo.search_cached(query, page, page_size)
        return [self._model_to_domain(m) for m in models]

    async def list_products(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """List all products."""
        models = await self._product_repo.list_all(skip, limit)
        return [self._model_to_domain(m) for m in models]

    async def update_product(self, product_id: UUID, data: dict[str, Any]) -> Optional[Product]:
        """Update product price/stock (invalidates cache)."""
        model = await self._product_repo.update_price_or_stock(product_id, data)
        if model is None:
            return None
        return self._model_to_domain(model)

    def _model_to_domain(self, model) -> Product:
        return Product(
            id=model.id,
            name=model.name,
            description=model.description,
            base_price=model.base_price,
            currency=model.currency,
            stock_available=model.stock_available,
            last_modified=model.last_modified,
            created_at=model.created_at,
        )
