from app.repositories import OrderRepository, OrderItemRepository
from app.schemas import OrderCreate, OrderUpdate, OrderInDB, OrderItemCreate, OrderItemUpdate, OrderItemInDB
from app.models import Order, OrderItem, OrderStatus
from app.database import get_db
from fastapi import Depends
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

class OrderService:
    def __init__(self, db: Session = Depends(get_db)):
        self.order_repo = OrderRepository(db)
        self.item_repo = OrderItemRepository(db)

    def get_order(self, order_id: int) -> Optional[OrderInDB]:
        order = self.order_repo.get(order_id)
        if order:
            return OrderInDB.from_orm(order)
        return None

    def get_orders(self, skip: int = 0, limit: int = 100) -> List[OrderInDB]:
        orders = self.order_repo.get_multi(skip=skip, limit=limit)
        return [OrderInDB.from_orm(o) for o in orders]

    def create_order(self, order_in: OrderCreate) -> OrderInDB:
        # Create order
        order_data = order_in.dict(exclude={"items"})
        order = self.order_repo.create(order_data)
        # Create order items
        for item_in in order_in.items:
            item_data = item_in.dict()
            item_data["order_id"] = order.id
            self.item_repo.create(item_data)
        # Re-fetch order with items
        order = self.order_repo.get(order.id)
        return OrderInDB.from_orm(order)

    def update_order(self, order_id: int, order_in: OrderUpdate) -> Optional[OrderInDB]:
        order_data = order_in.dict(exclude_unset=True)
        order = self.order_repo.update(order_id, order_data)
        if order:
            return OrderInDB.from_orm(order)
        return None

    def delete_order(self, order_id: int) -> bool:
        # Delete items first
        items = self.item_repo.get_by_order(order_id)
        for item in items:
            self.item_repo.delete(item.id)
        return self.order_repo.delete(order_id)

    # Workflow methods
    def accept_order(self, order_id: int) -> Optional[OrderInDB]:
        order = self.order_repo.get(order_id)
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.ACCEPTED
            order.updated_at = datetime.utcnow()
            self.order_repo.db.commit()
            self.order_repo.db.refresh(order)
            return OrderInDB.from_orm(order)
        return None

    def create_invoice(self, order_id: int) -> Optional[OrderInDB]:
        order = self.order_repo.get(order_id)
        if order and order.status == OrderStatus.ACCEPTED:
            # In a real system, we would create an invoice record in a separate table
            # For simplicity, we just update the order status to INVOICED
            order.status = OrderStatus.INVOICED
            order.updated_at = datetime.utcnow()
            self.order_repo.db.commit()
            self.order_repo.db.refresh(order)
            return OrderInDB.from_orm(order)
        return None

    def verify_payment(self, order_id: int) -> Optional[OrderInDB]:
        order = self.order_repo.get(order_id)
        if order and order.status == OrderStatus.INVOICED:
            # In a real system, we would check payment status from a payment table
            # For simplicity, we assume payment is verified and move to PAID
            order.status = OrderStatus.PAID
            order.updated_at = datetime.utcnow()
            self.order_repo.db.commit()
            self.order_repo.db.refresh(order)
            return OrderInDB.from_orm(order)
        return None

    def ship_order(self, order_id: int) -> Optional[OrderInDB]:
        order = self.order_repo.get(order_id)
        if order and order.status == OrderStatus.PAID:
            order.status = OrderStatus.SHIPPED
            order.updated_at = datetime.utcnow()
            self.order_repo.db.commit()
            self.order_repo.db.refresh(order)
            return OrderInDB.from_orm(order)
        return None

    def close_order(self, order_id: int) -> Optional[OrderInDB]:
        order = self.order_repo.get(order_id)
        if order and order.status == OrderStatus.SHIPPED:
            order.status = OrderStatus.CLOSED
            order.updated_at = datetime.utcnow()
            self.order_repo.db.commit()
            self.order_repo.db.refresh(order)
            return OrderInDB.from_orm(order)
        return None