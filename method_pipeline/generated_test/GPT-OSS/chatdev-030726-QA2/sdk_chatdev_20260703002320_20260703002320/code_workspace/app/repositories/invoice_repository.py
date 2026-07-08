"""
Invoice repository extending BaseRepository.
"""

from app.models.invoice import Invoice
from app.repositories.base import BaseRepository

class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self):
        super().__init__(Invoice)
