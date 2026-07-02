"""
Payment repository extending BaseRepository.
"""

from app.models.payment import Payment
from app.repositories.base import BaseRepository

class PaymentRepository(BaseRepository[Payment]):
    def __init__(self):
        super().__init__(Payment)
