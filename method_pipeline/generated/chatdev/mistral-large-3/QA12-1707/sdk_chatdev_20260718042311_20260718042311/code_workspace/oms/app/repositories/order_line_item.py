"""
Order Line Item repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.order_line_item import OrderLineItem
from app.schemas.order_line_item import OrderLineItemCreate


class OrderLineItemRepository:
    """Order Line Item repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, line_item: OrderLineItemCreate, order_id: int) -> OrderLineItem:
        """Create a new order line item."""
        db_line_item = OrderLineItem(**line_item.model_dump(), order_id=order_id)
        self.db.add(db_line_item)
        self.db.commit()
        self.db.refresh(db_line_item)
        return db_line_item

    def get_by_id(self, line_item_id: int) -> Optional[OrderLineItem]:
        """Get order line item by ID."""
        return self.db.query(OrderLineItem).filter(OrderLineItem.id == line_item_id).first()

    def list_by_order(self, order_id: int) -> list[OrderLineItem]:
        """List all line items for an order."""
        return self.db.query(OrderLineItem).filter(OrderLineItem.order_id == order_id).all()