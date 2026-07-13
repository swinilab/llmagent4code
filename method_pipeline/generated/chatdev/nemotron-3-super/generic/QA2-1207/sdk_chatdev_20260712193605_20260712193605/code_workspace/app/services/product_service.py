from app.repositories import ProductRepository
from app.schemas import ProductCreate, ProductUpdate, ProductInDB
from app.models import Product
from app.database import get_db
from fastapi import Depends
from typing import List, Optional
from sqlalchemy.orm import Session

class ProductService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = ProductRepository(db)

    def get_product(self, product_id: int) -> Optional[ProductInDB]:
        product = self.repository.get(product_id)
        if product:
            return ProductInDB.from_orm(product)
        return None

    def get_products(self, skip: int = 0, limit: int = 100) -> List[ProductInDB]:
        products = self.repository.get_multi(skip=skip, limit=limit)
        return [ProductInDB.from_orm(p) for p in products]

    def create_product(self, product_in: ProductCreate) -> ProductInDB:
        product = self.repository.create(product_in.dict())
        return ProductInDB.from_orm(product)

    def update_product(self, product_id: int, product_in: ProductUpdate) -> Optional[ProductInDB]:
        product_data = product_in.dict(exclude_unset=True)
        product = self.repository.update(product_id, product_data)
        if product:
            return ProductInDB.from_orm(product)
        return None

    def delete_product(self, product_id: int) -> bool:
        return self.repository.delete(product_id)