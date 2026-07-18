"""
Product repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate


class ProductRepository:
    """Product repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, product: ProductCreate) -> Product:
        """Create a new product."""
        db_product = Product(**product.model_dump())
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        return self.db.query(Product).filter(Product.id == product_id).first()

    def list_all(self) -> list[Product]:
        """List all products."""
        return self.db.query(Product).all()