"""
Invoice repository.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from oms.models.entities import InvoiceModel
from oms.models.enums import InvoiceStatus
from oms.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[InvoiceModel]):
    def __init__(self, db: Session):
        super().__init__(InvoiceModel, db)

    def get_by_order(self, order_id: str) -> List[InvoiceModel]:
        return (
            self.db.query(InvoiceModel)
            .filter(InvoiceModel.order_id == order_id)
            .all()
        )

    def get_by_status(self, status: InvoiceStatus) -> List[InvoiceModel]:
        return (
            self.db.query(InvoiceModel)
            .filter(InvoiceModel.status == status)
            .all()
        )
