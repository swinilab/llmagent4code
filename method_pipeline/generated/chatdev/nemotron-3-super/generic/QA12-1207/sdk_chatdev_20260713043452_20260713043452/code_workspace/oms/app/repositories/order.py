from sqlalchemy.orm import Session
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate, OrderUpdate
from app.models.order_item import OrderItem
from app.schemas.order_item import OrderItemCreate

class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int):
        return self.db.query(Order).filter(Order.id == id).first()

    def get_multi(self, skip: int = 0, limit: int = 100):
        return self.db.query(Order).offset(skip).limit(limit).all()

    def create(self, obj_in: OrderCreate):
        db_obj = Order(
            customer_id=obj_in.customer_id,
            status=obj_in.status
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Order, obj_in: OrderUpdate):
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def remove(self, id: int):
        obj = self.db.query(Order).get(id)
        self.db.delete(obj)
        self.db.commit()
        return obj

    # Additional methods for order items
    def add_item(self, order_id: int, item_in: OrderItemCreate):
        db_obj = OrderItem(
            order_id=order_id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_price=item_in.unit_price,
            total_price=item_in.total_price
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_items(self, order_id: int):
        return self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()