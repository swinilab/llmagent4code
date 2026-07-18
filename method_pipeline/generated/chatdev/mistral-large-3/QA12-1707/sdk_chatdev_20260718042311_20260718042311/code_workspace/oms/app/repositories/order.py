"""
Order repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate


class OrderRepository:
    """Order repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, order: OrderCreate) -> Order:
        """Create a new order."""
        db_order = Order(**order.model_dump(exclude={"line_items"}))
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()

    def update_status(self, order_id: int, status: OrderStatus) -> Optional[Order]:
        """Update order status."""
        db_order = self.get_by_id(order_id)
        if db_order:
            db_order.status = status
            self.db.commit()
            self.db.refresh(db_order)
        return db_order

    def list_all(self) -> list[Order]:
        """List all orders."""
        return self.db.query(Order).all()