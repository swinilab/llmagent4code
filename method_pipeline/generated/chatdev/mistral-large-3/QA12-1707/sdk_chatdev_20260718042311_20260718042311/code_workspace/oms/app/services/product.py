"""
Product service layer.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductRead


class ProductService:
    """Product service."""

    def __init__(self, db: Session):
        self.repo = ProductRepository(db)

    def create_product(self, product: ProductCreate) -> ProductRead:
        """Create a new product."""
        db_product = self.repo.create(product)
        return ProductRead.model_validate(db_product)

    def get_product(self, product_id: int) -> Optional[ProductRead]:
        """Get product by ID."""
        db_product = self.repo.get_by_id(product_id)
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")
        return ProductRead.model_validate(db_product)

    def list_products(self) -> list[ProductRead]:
        """List all products."""
        db_products = self.repo.list_all()
        return [ProductRead.model_validate(product) for product in db_products]