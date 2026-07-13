from sqlalchemy.orm import Session
from fastapi import Depends
from typing import List, Optional
from . import models, schemas, repositories
from .database import get_db
from .utils import retry, CircuitBreaker
import random
import time
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError, DisconnectionError
from .payment_gateway import PaymentGateway

class UserService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = repositories.UserRepository(models.User, db)

    def get_user(self, user_id: int) -> Optional[models.User]:
        return self.repository.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[models.User]:
        return self.repository.get_by_email(email)

    def create_user(self, user_in: schemas.UserCreate) -> models.User:
        user_data = user_in.dict()
        # In a real app, hash the password
        user_data["hashed_password"] = user_data.pop("password")
        return self.repository.create(user_data)

    def update_user(self, user_id: int, user_in: schemas.UserUpdate) -> Optional[models.User]:
        user_data = user_in.dict(exclude_unset=True)
        return self.repository.update(user_id, user_data)

    def delete_user(self, user_id: int) -> bool:
        return self.repository.delete(user_id)

class ProductService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = repositories.ProductRepository(models.Product, db)

    def get_product(self, product_id: int) -> Optional[models.Product]:
        return self.repository.get(product_id)

    def get_products(self, skip: int = 0, limit: int = 100) -> List[models.Product]:
        return self.repository.get_multi(skip=skip, limit=limit)

    def create_product(self, product_in: schemas.ProductCreate) -> models.Product:
        return self.repository.create(product_in.dict())

    def update_product(self, product_id: int, product_in: schemas.ProductUpdate) -> Optional[models.Product]:
        product_data = product_in.dict(exclude_unset=True)
        return self.repository.update(product_id, product_data)

    def delete_product(self, product_id: int) -> bool:
        return self.repository.delete(product_id)

class OrderService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = repositories.OrderRepository(models.Order, db)
        self.item_repo = repositories.OrderItemRepository(models.OrderItem, db)
        self.payment_repo = repositories.PaymentRepository(models.Payment, db)
        self.invoice_repo = repositories.InvoiceRepository(models.Invoice, db)
    # Circuit breaker for payment gateway
    _payment_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

    @staticmethod
    @retry(exceptions=(Exception,), tries=3, delay=1, backoff=2)
    def _process_payment_with_gateway(amount: int, method: str) -> bool:
        """Simulate a payment gateway call that may fail."""
        # Simulate random failure
        if random.random() < 0.3:  # 30% chance of failure
            raise Exception("Payment gateway temporarily unavailable")
        # Simulate network delay
        time.sleep(0.1)
        return True

    @classmethod
    def _charge_payment(cls, amount: int, method: str) -> bool:
        """Attempt to charge via payment gateway with circuit breaker."""
        return cls._payment_cb.call(cls._process_payment_with_gateway, amount, method)

    def get_order(self, order_id: int) -> Optional[models.Order]:
        return self.repository.get(order_id)

    def get_orders(self, skip: int = 0, limit: int = 100) -> List[models.Order]:
        return self.repository.get_multi(skip=skip, limit=limit)

    def create_order(self, order_in: schemas.OrderCreate) -> models.Order:
        # Create order
        order_data = order_in.dict(exclude={"items"})
        order = self.repository.create(order_data)
        # Create order items
        total_amount = 0
        for item_in in order_in.items:
            item_data = item_in.dict()
            item_data["order_id"] = order.id
            item = self.item_repo.create(item_data)
            total_amount += item.unit_price * item.quantity
        # Update order total
        order.total_amount = total_amount
        self.repository.update(order.id, {"total_amount": total_amount})
        return order

    def update_order(self, order_id: int, order_in: schemas.OrderUpdate) -> Optional[models.Order]:
        order_data = order_in.dict(exclude_unset=True)
        return self.repository.update(order_id, order_data)

    def delete_order(self, order_id: int) -> bool:
        # Delete items first
        items = self.item_repo.get_by_order(order_id)
        for item in items:
            self.item_repo.delete(item.id)
        return self.repository.delete(order_id)

    # Workflow methods
    def accept_order(self, order_id: int) -> Optional[models.Order]:
        order = self.get_order(order_id)
        if order and order.status == models.OrderStatus.PENDING:
            order.status = models.OrderStatus.ACCEPTED
            return self.repository.update(order_id, {"status": models.OrderStatus.ACCEPTED})
        return None

    def create_invoice_for_order(self, order_id: int, billing_info: str) -> Optional[models.Invoice]:
        order = self.get_order(order_id)
        if not order or order.status != models.OrderStatus.ACCEPTED:
            return None
        # Check if invoice already exists
        existing_invoice = self.invoice_repo.get_by_order(order_id)
        if existing_invoice:
            return existing_invoice
        # Create invoice
        invoice_data = {
            "order_id": order.id,
            "billing_info": billing_info,
            "amount": order.total_amount,
            "issue_date": datetime.utcnow(),
            "due_date": datetime.utcnow() + timedelta(days=30),  # Net 30
            "status": models.InvoiceStatus.DRAFT
        }
        invoice = self.invoice_repo.create(invoice_data)
        # Update order with invoice reference
        self.repository.update(order.id, {"invoice_id": invoice.id})
        return invoice

    def record_payment(self, order_id: int, amount: int, method: str) -> Optional[models.Payment]:
        order = self.get_order(order_id)
        if not order:
            return None
        payment_data = {
            "order_id": order.id,
            "amount": amount,
            "method": method,
            "status": models.PaymentStatus.PENDING,
            "timestamp": datetime.utcnow()
        }
        payment = self.payment_repo.create(payment_data)
        # If payment amount matches order total, mark as paid
        if amount >= order.total_amount:
            payment.status = models.PaymentStatus.COMPLETED
            self.payment_repo.update(payment.id, {"status": models.PaymentStatus.COMPLETED})
            # Update order status to paid
            self.repository.update(order.id, {"status": models.OrderStatus.PAID})
        return payment

    def verify_payment(self, payment_id: int) -> Optional[models.Payment]:
        payment = self.payment_repo.get(payment_id)
        if payment and payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.COMPLETED
            updated_payment = self.payment_repo.update(payment_id, {"status": models.PaymentStatus.COMPLETED})
            # Update order status to paid
            order = self.get_order(payment.order_id)
            if order:
                self.repository.update(order.id, {"status": models.OrderStatus.PAID})
            return updated_payment
        return None

    def ship_order(self, order_id: int) -> Optional[models.Order]:
        order = self.get_order(order_id)
        if order and order.status == models.OrderStatus.PAID:
            order.status = models.OrderStatus.SHIPPED
            return self.repository.update(order_id, {"status": models.OrderStatus.SHIPPED})
        return None

    def close_order(self, order_id: int) -> Optional[models.Order]:
        order = self.get_order(order_id)
        if order and order.status == models.OrderStatus.SHIPPED:
            order.status = models.OrderStatus.CLOSED
            return self.repository.update(order_id, {"status": models.OrderStatus.CLOSED})
        return None

class PaymentService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = repositories.PaymentRepository(models.Payment, db)

    def get_payment(self, payment_id: int) -> Optional[models.Payment]:
        return self.repository.get(payment_id)

    def get_payments_by_order(self, order_id: int) -> List[models.Payment]:
    def create_payment(self, payment_in: schemas.PaymentCreate) -> models.Payment:

    def create_payment(self, payment_in: schemas.PaymentCreate) -> models.Packet:
        return self.repository.create(payment_in.dict())

    def update_payment(self, payment_id: int, payment_in: schemas.PaymentUpdate) -> Optional[models.Payment]:
        payment_data = payment_in.dict(exclude_unset=True)
        return self.repository.update(payment_id, payment_data)

    def delete_payment(self, payment_id: int) -> bool:
        return self.repository.delete(payment_id)

class InvoiceService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = repositories.InvoiceRepository(models.Invoice, db)

    def get_invoice(self, invoice_id: int) -> Optional[models.Invoice]:
        return self.repository.get(invoice_id)

    def get_invoice_by_order(self, order_id: int) -> Optional[models.Invoice]:
        return self.repository.get_by_order(order_id)

    def create_invoice(self, invoice_in: schemas.InvoiceCreate) -> models.Invoice:
        return self.repository.create(invoice_in.dict())

    def update_invoice(self, invoice_id: int, invoice_in: schemas.InvoiceUpdate) -> Optional[models.Invoice]:
        invoice_data = invoice_in.dict(exclude_unset=True)
        return self.repository.update(invoice_id, invoice_data)

    def delete_invoice(self, invoice_id: int) -> bool:
        return self.repository.delete(invoice_id)

    def approve_invoice(self, invoice_id: int) -> Optional[models.Invoice]:
        invoice = self.get_invoice(invoice_id)
        if invoice and invoice.status == models.InvoiceStatus.DRAFT:
            invoice.status = models.InvoiceStatus.APPROVED
            return self.repository.update(invoice_id, {"status": models.InvoiceStatus.APPROVED})
        return None

    def mark_invoice_as_paid(self, invoice_id: int) -> Optional[models.Invoice]:
        invoice = self.get_invoice(invoice_id)
        if invoice and invoice.status == models.InvoiceStatus.APPROVED:
            invoice.status = models.InvoiceStatus.PAID
            return self.repository.update(invoice_id, {"status": models.InvoiceStatus.PAID})
        return None