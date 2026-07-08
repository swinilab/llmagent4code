"""
Product service handling business logic.
"""

from sqlalchemy.orm import Session
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate

class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductRepository()

    def create_product(self, payload: ProductCreate):
        return self.repo.create(self.db, payload.model_dump())

    def get_product(self, product_id: int):
        return self.repo.get(self.db, product_id)

    def update_product(self, product_id: int, payload: ProductUpdate):
        db_obj = self.repo.get(self.db, product_id)
        if not db_obj:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        return self.repo.update(self.db, db_obj, update_data)

    def delete_product(self, product_id: int):
        return self.repo.delete(self.db, product_id)
