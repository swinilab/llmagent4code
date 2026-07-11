"""
Payment repository.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from oms.models.entities import PaymentModel
from oms.models.enums import PaymentStatus
from oms.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[PaymentModel]):
    def __init__(self, db: Session):
        super().__init__(PaymentModel, db)

    def get_by_order(self, order_id: str) -> List[PaymentModel]:
        return (
            self.db.query(PaymentModel)
            .filter(PaymentModel.order_id == order_id)
            .all()
        )

    def get_by_status(self, status: PaymentStatus) -> List[PaymentModel]:
        return (
            self.db.query(PaymentModel)
            .filter(PaymentModel.status == status)
            .all()
        )
