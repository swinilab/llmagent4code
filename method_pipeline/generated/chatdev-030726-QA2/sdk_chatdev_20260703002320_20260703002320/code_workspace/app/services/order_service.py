"""
Order service orchestrating order lifecycle.
"""

from sqlalchemy.orm import Session
from app.repositories.order_repository import OrderRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.order import OrderCreate, OrderUpdate, OrderLineItemCreate
from typing import List

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrderRepository()
        self.customer_repo = CustomerRepository()

    def place_order(self, payload: OrderCreate):
        # Verify customer exists
        customer = self.customer_repo.get(self.db, payload.customer_id)
        if not customer:
            raise ValueError("Customer not found")
        # Create order without line items first
        order_data = payload.model_dump(exclude={"line_items"})
        order = self.repo.create(self.db, order_data)
        # Add line items and compute total
        items = [item.model_dump() for item in payload.line_items]
        self.repo.add_line_items(self.db, order, items)
        return order

    def get_order(self, order_id: int):
        return self.repo.get(self.db, order_id)

    def update_status(self, order_id: int, status: str):
        order = self.repo.get(self.db, order_id)
        if not order:
            raise ValueError("Order not found")
        return self.repo.update(self.db, order, {"status": status})

    def list_orders(self, skip: int = 0, limit: int = 100):
        return self.repo.get_all(self.db, skip, limit)
