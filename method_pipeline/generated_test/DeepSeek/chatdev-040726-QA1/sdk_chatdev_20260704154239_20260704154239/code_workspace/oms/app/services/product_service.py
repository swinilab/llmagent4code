"""
Service layer for Product operations.
"""
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Business logic for managing products."""

    @staticmethod
    def create(db: Session, data: ProductCreate, commit: bool = True) -> Product:
        product = Product(**data.model_dump())
        db.add(product)
        if commit:
            db.commit()
            db.refresh(product)
        else:
            db.flush()
        return product

    @staticmethod
    def get_by_id(db: Session, product_id: str) -> Product | None:
        return db.query(Product).filter(Product.id == product_id).first()

    @staticmethod
    def search(db: Session, query: str = "", skip: int = 0, limit: int = 100) -> list[Product]:
        q = db.query(Product)
        if query:
            q = q.filter(Product.name.ilike(f"%{query}%") | Product.description.ilike(f"%{query}%"))
        return q.offset(skip).limit(limit).all()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Product]:
        return db.query(Product).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, product_id: str, data: ProductUpdate, commit: bool = True) -> Product | None:
        product = ProductService.get_by_id(db, product_id)
        if not product:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        if commit:
            db.commit()
            db.refresh(product)
        else:
            db.flush()
        return product

    @staticmethod
    def delete(db: Session, product_id: str, commit: bool = True) -> bool:
        product = ProductService.get_by_id(db, product_id)
        if not product:
            return False
        db.delete(product)
        if commit:
            db.commit()
        else:
            db.flush()
        return True
