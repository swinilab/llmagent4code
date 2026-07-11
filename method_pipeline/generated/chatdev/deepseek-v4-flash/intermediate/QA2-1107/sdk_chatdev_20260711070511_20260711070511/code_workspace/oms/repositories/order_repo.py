"""
Order repository with line-item support.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from oms.models.entities import OrderLineItemModel, OrderModel
from oms.models.enums import OrderStatus
from oms.repositories.base import BaseRepository


class OrderRepository(BaseRepository[OrderModel]):
    def __init__(self, db: Session):
        super().__init__(OrderModel, db)

    def get_by_customer(self, customer_id: str) -> List[OrderModel]:
        return (
            self.db.query(OrderModel)
            .filter(OrderModel.customer_id == customer_id)
            .all()
        )

    def get_by_status(self, status: OrderStatus) -> List[OrderModel]:
        return (
            self.db.query(OrderModel)
            .filter(OrderModel.status == status)
            .all()
        )

    def add_line_item(self, order_id: str, item: OrderLineItemModel) -> OrderLineItemModel:
        item.order_id = order_id
        self.db.add(item)
        self.db.flush()
        return item

    def get_line_items(self, order_id: str) -> List[OrderLineItemModel]:
        return (
            self.db.query(OrderLineItemModel)
            .filter(OrderLineItemModel.order_id == order_id)
            .all()
        )
