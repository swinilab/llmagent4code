"""
Customer repository extending BaseRepository.
"""

from app.models.customer import Customer
from app.repositories.base import BaseRepository

class CustomerRepository(BaseRepository[Customer]):
    def __init__(self):
        super().__init__(Customer)
