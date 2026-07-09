"""Invoice repository."""

from app.repositories.base import BaseRepository
from app.repositories.orm_models import InvoiceModel


class InvoiceRepository(BaseRepository[InvoiceModel]):
    def __init__(self, session):
        super().__init__(InvoiceModel, session)
