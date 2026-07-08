from sqlalchemy.orm import Session
from typing import List, Optional
from app import models

# Customer repository
class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, customer_id: int) -> Optional[models.Customer]:
        return self.db.query(models.Customer).filter(models.Customer.id == customer_id).first()

    def create(self, obj_in: models.Customer) -> models.Customer:
        self.db.add(obj_in)
        self.db.commit()
        self.db.refresh(obj_in)
        return obj_in

# Product repository
class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, product_id: int) -> Optional[models.Product]:
        return self.db.query(models.Product).filter(models.Product.id == product_id).first()

    def create(self, obj_in: models.Product) -> models.Product:
        self.db.add(obj_in)
        self.db.commit()
        self.db.refresh(obj_in)
        return obj_in

    def list(self, skip: int = 0, limit: int = 100) -> List[models.Product]:
        return self.db.query(models.Product).offset(skip).limit(limit).all()

# Order repository
class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, order_id: int) -> Optional[models.Order]:
        return self.db.query(models.Order).filter(models.Order.id == order_id).first()

    def create(self, order: models.Order) -> models.Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update_status(self, order: models.Order, new_status: models.OrderStatus) -> models.Order:
        order.status = new_status
        self.db.commit()
        self.db.refresh(order)
        return order

# Payment repository
class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_order(self, order_id: int) -> Optional[models.Payment]:
        return self.db.query(models.Payment).filter(models.Payment.order_id == order_id).first()

    def create(self, payment: models.Payment) -> models.Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update_status(self, payment: models.Payment, new_status: models.PaymentStatus) -> models.Payment:
        payment.status = new_status
        self.db.commit()
        self.db.refresh(payment)
        return payment

# Invoice repository
class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_order(self, order_id: int) -> Optional[models.Invoice]:
        return self.db.query(models.Invoice).filter(models.Invoice.order_id == order_id).first()

    def create(self, invoice: models.Invoice) -> models.Invoice:
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def update_status(self, invoice: models.Invoice, new_status: models.InvoiceStatus) -> models.Invoice:
        invoice.status = new_status
        self.db.commit()
        self.db.refresh(invoice)
        return invoice
