"""
Customer repository.
"""
from sqlalchemy.orm import Session

from oms.models.entities import CustomerModel
from oms.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[CustomerModel]):
    def __init__(self, db: Session):
        super().__init__(CustomerModel, db)
