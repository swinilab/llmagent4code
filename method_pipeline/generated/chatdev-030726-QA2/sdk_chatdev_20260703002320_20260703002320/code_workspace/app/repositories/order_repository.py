"""
Order repository with helper methods.
"""

from sqlalchemy.orm import Session
from typing import List
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.repositories.base import BaseRepository

class OrderRepository(BaseRepository[Order]):
    def __init__(self):
        super().__init__(Order)

    def add_line_items(self, db: Session, order: Order, items_data: List[dict]) -> List[OrderLineItem]:
        line_items = []
        total = 0.0
        for item in items_data:
            line = OrderLineItem(**item, order_id=order.id)
            db.add(line)
            line_items.append(line)
            total += item["unit_price"] * item["quantity"]
        order.total_amount = total
        db.commit()
        for line in line_items:
            db.refresh(line)
        db.refresh(order)
        return line_items
