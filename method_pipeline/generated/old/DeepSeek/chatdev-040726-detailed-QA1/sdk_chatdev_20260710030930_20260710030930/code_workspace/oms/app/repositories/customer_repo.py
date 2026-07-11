"""Customer repository."""

from app.repositories.base import BaseRepository
from app.repositories.orm_models import CustomerModel


class CustomerRepository(BaseRepository[CustomerModel]):
    def __init__(self, session):
        super().__init__(CustomerModel, session)
