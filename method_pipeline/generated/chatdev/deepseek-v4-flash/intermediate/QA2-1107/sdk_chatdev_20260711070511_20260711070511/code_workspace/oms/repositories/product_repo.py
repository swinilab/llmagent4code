"""
Product repository.
"""
from sqlalchemy.orm import Session

from oms.models.entities import ProductModel
from oms.repositories.base import BaseRepository


class ProductRepository(BaseRepository[ProductModel]):
    def __init__(self, db: Session):
        super().__init__(ProductModel, db)
