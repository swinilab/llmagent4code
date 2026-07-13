from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate, OrderUpdate
from app.schemas.order_item import OrderItemCreate

class OrderService:
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    def get(self, id: int):
        return self.order_repository.get(id)

    def get_multi(self, skip: int = 0, limit: int = 100):
        return self.order_repository.get_multi(skip, limit)

    def create(self, obj_in: OrderCreate):
        return self.order_repository.create(obj_in)

    def update(self, id: int, obj_in: OrderUpdate):
        obj = self.order_repository.get(id)
        if obj:
            return self.order_repository.update(obj, obj_in)
        return None

    def delete(self, id: int):
        return self.order_repository.remove(id)

    def add_item(self, order_id: int, item_in: OrderItemCreate):
        return self.order_repository.add_item(order_id, item_in)

    def get_items(self, order_id: int):
        return self.order_repository.get_items(order_id)