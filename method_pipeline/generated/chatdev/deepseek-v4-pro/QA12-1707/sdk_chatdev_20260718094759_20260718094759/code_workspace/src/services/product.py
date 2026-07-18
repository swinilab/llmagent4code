"""Product business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product import Product
from src.repositories.product import ProductRepository
from src.schemas.product import ProductCreate, ProductUpdate
from src.utils.exceptions import NotFoundError


class ProductService:
    """Orchestrates product catalogue operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = ProductRepository(session)

    async def create(self, payload: ProductCreate) -> Product:
        """Add a new product to the catalogue."""
        product = Product(
            description=payload.description,
            base_price=payload.base_price,
            currency=payload.currency,
        )
        return await self.repo.add(product)

    async def get(self, product_id: str) -> Product:
        """Retrieve a product by ID."""
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        return product

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Product]:
        """List all products with pagination."""
        return await self.repo.list_all(limit=limit, offset=offset)

    async def update(self, product_id: str, payload: ProductUpdate) -> Product:
        """Partially update a product."""
        product = await self.get(product_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        await self.repo.session.flush()
        return product

    async def delete(self, product_id: str) -> None:
        """Remove a product."""
        product = await self.get(product_id)
        await self.repo.delete(product)

    async def search(self, fragment: str) -> list[Product]:
        """Search products by description."""
        return await self.repo.search_by_description(fragment)
