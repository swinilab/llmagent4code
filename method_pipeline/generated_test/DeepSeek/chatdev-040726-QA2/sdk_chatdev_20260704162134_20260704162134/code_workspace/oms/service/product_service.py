"""
Product service: CRUD for products.
"""

from uuid import UUID

from oms.domain.models import Product, CreateProductRequest
from oms.repository.in_memory import InMemoryProductRepository


class ProductService:
    """Business logic for Product operations."""

    def __init__(self, repo: InMemoryProductRepository) -> None:
        self._repo = repo

    def create(self, request: CreateProductRequest) -> Product:
        """Create a new product."""
        product = Product(
            description=request.description,
            base_price=request.base_price,
        )
        return self._repo.save(product)

    def get_by_id(self, product_id: UUID) -> Product | None:
        """Retrieve a product by ID."""
        return self._repo.find_by_id(product_id)

    def list_all(self) -> list[Product]:
        """List all products."""
        return self._repo.find_all()
