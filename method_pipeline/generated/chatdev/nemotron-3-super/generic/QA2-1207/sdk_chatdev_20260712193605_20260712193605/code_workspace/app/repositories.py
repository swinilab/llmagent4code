from typing import List, Optional, Type, TypeVar, Generic
from sqlalchemy.orm import Session
from . import models

ModelType = TypeVar("ModelType", bound=models.Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, id: int, obj_in: dict) -> Optional[ModelType]:
        db_obj = self.get(id)
        if db_obj:
            for field, value in obj_in.items():
                setattr(db_obj, field, value)
            self.db.commit()
            self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:
        db_obj = self.get(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
            return True
        return False

# Specific repositories
class UserRepository(BaseRepository[models.User]):
    def get_by_email(self, email: str) -> Optional[models.User]:
        return self.db.query(models.User).filter(models.User.email == email).first()

class ProductRepository(BaseRepository[models.Product]):
    def get_active(self, skip: int = 0, limit: int = 100) -> List[models.Product]:
        return self.db.query(models.Product).filter(models.Product.is_active == True).offset(skip).limit(limit).all()

class OrderRepository(BaseRepository[models.Order]):
    def get_by_customer(self, customer_id: int, skip: int = 0, limit: int = 100) -> List[models.Order]:
        return self.db.query(models.Order).filter(models.Order.customer_id == customer_id).offset(skip).limit(limit).all()

    def get_by_status(self, status: models.OrderStatus, skip: int = 0, limit: int = 100) -> List[models.Order]:
        return self.db.query(models.Order).filter(models.Order.status == status).offset(skip).limit(limit).all()

class OrderItemRepository(BaseRepository[models.OrderItem]):
    def get_by_order(self, order_id: int) -> List[models.OrderItem]:
        return self.db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).all()

class PaymentRepository(BaseRepository[models.Payment]):
    def get_by_order(self, order_id: int) -> List[models.Payment]:
        return self.db.query(models.Payment).filter(models.Payment.order_id == order_id).all()

class InvoiceRepository(BaseRepository[models.Invoice]):
    def get_by_order(self, order_id: int) -> Optional[models.Invoice]:
        return self.db.query(models.Invoice).filter(models.Invoice.order_id == order_id).first()