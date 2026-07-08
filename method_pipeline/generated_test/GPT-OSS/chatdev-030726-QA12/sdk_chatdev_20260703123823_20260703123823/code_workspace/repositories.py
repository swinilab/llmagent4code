"""Repository layer: direct DB access using SQLAlchemy sessions.
Each repository is a thin wrapper that can be injected into services.
"""
from sqlalchemy.orm import Session
from models import Customer, Product, Order, OrderLineItem, Payment, Invoice
from typing import List, Optional

# Customer repository
class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def get(self, customer_id: int) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        return self.db.query(Customer).offset(skip).limit(limit).all()

# Product repository
class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[Product]:
        return self.db.query(Product).offset(skip).limit(limit).all()

# Order repository
class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def update_status(self, order: Order, new_status) -> Order:
        order.status = new_status
        self.db.commit()
        self.db.refresh(order)
        return order

    def list(self, skip: int = 0, limit: int = 100) -> List[Order]:
        return self.db.query(Order).offset(skip).limit(limit).all()

# OrderLineItem repository
class OrderLineItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, items: List[OrderLineItem]):
        self.db.add_all(items)
        self.db.commit()
        for item in items:
            self.db.refresh(item)
        return items

# Payment repository
class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_by_order(self, order_id: int) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.order_id == order_id).first()

# Invoice repository
class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_by_order(self, order_id: int) -> Optional[Invoice]:
        return self.db.query(Invoice).filter(Invoice.order_id == order_id).first()
