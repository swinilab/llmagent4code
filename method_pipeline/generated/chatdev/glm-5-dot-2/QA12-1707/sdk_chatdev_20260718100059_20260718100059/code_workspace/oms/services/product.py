"""
Product service — business logic for product management and search.

Provides CRUD and keyword/price search with pagination.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.product import Product
from oms.repositories.product import ProductRepository
from oms.schemas.product import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)


class ProductService:
    """Business logic for Product entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProductRepository(session)

    async def create_product(self, data: ProductCreate) -> Product:
        """Create a new product."""
        product = await self.repo.create(
            description=data.description,
            base_price=data.base_price,
            currency=data.currency,
        )
        await self.session.commit()
        logger.info("Created product %s", product.id)
        return product

    async def get_product(self, product_id: str) -> Product | None:
        """Fetch a product by ID."""
        return await self.repo.get_by_id(product_id)

    async def list_products(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Product], int]:
        """List products with pagination."""
        offset = (page - 1) * page_size
        return await self.repo.get_all(offset=offset, limit=page_size)

    async def search_products(
        self,
        query: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        currency: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        """
        Search products by description keyword and/or price range.

        This is a core journey endpoint (NFR 1.1) — the query is
        executed with a single indexed ILIKE scan.
        """
        offset = (page - 1) * page_size
        return await self.repo.search(
            query=query,
            min_price=min_price,
            max_price=max_price,
            currency=currency,
            offset=offset,
            limit=page_size,
        )

    async def update_product(
        self, product_id: str, data: ProductUpdate
    ) -> Product | None:
        """Update a product's fields."""
        product = await self.repo.get_by_id(product_id)
        if product is None:
            return None
        updates = data.model_dump(exclude_unset=True)
        product = await self.repo.update(product, **updates)
        await self.session.commit()
        logger.info("Updated product %s", product_id)
        return product

    async def delete_product(self, product_id: str) -> bool:
        """Delete a product. Returns True if deleted, False if not found."""
        product = await self.repo.get_by_id(product_id)
        if product is None:
            return False
        await self.repo.delete(product)
        await self.session.commit()
        logger.info("Deleted product %s", product_id)
        return True