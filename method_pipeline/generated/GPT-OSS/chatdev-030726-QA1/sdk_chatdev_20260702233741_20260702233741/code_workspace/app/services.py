from typing import List, Optional
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.repositories import (
    CustomerRepository,
    ProductRepository,
    OrderRepository,
    PaymentRepository,
    InvoiceRepository,
)
# Import async tasks
from app.queue import verify_payment_task, ship_order_task

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.customer_repo = CustomerRepository(db)
        self.product_repo = ProductRepository(db)
        self.order_repo = OrderRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.invoice_repo = InvoiceRepository(db)

    def place_order(self, order_in: schemas.OrderCreate) -> models.Order:
        # Validate customer
        customer = self.customer_repo.get(order_in.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        # Build order and line items
        order = models.Order(
            customer_id=order_in.customer_id,
            currency=order_in.currency,
            status=models.OrderStatus.CREATED,
        )
        total = Decimal('0')
        line_items = []
        for item in order_in.line_items:
            product = self.product_repo.get(item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            li = models.OrderLineItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )
            total += item.total_price
            line_items.append(li)
        order.total_amount = total
        order.line_items = line_items
        return self.order_repo.create(order)

    def get_order(self, order_id: int) -> models.Order:
        return self.order_repo.get(order_id)

    def accept_order(self, order_id: int) -> models.Order:
        order = self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != models.OrderStatus.CREATED:
            raise HTTPException(status_code=400, detail="Order cannot be accepted in current state")
        return self.order_repo.update_status(order, models.OrderStatus.ACCEPTED)

    def create_invoice(self, order_id: int, invoice_in: schemas.InvoiceCreate) -> models.Invoice:
        order = self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != models.OrderStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail="Order must be accepted before invoicing")
        invoice = models.Invoice(
            order_id=order_id,
            billing_info=invoice_in.billing_info,
            amount=invoice_in.amount,
            due_date=invoice_in.due_date,
            status=models.InvoiceStatus.ISSUED,
        )
        created = self.invoice_repo.create(invoice)
        # link to order
        order.invoice_id = created.id
        order.status = models.OrderStatus.INVOICED
        self.db.commit()
        self.db.refresh(order)
        return created

    def record_payment(self, payment_in: schemas.PaymentCreate) -> models.Payment:
        order = self.order_repo.get(payment_in.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status not in [models.OrderStatus.INVOICED, models.OrderStatus.PAID]:
            raise HTTPException(status_code=400, detail="Order not ready for payment")
        payment = models.Payment(
            order_id=payment_in.order_id,
            amount=payment_in.amount,
            method=payment_in.method,
            status=models.PaymentStatus.PENDING,
        )
        created = self.payment_repo.create(payment)
        # Enqueue async verification task (initially pending)
        verify_payment_task.delay(created.id, False)
        return created

    def verify_payment(self, payment_id: int, success: bool) -> models.Payment:
        payment = self.db.query(models.Payment).filter(models.Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        new_status = models.PaymentStatus.COMPLETED if success else models.PaymentStatus.FAILED
        payment = self.payment_repo.update_status(payment, new_status)
        if success:
            order = payment.order
            order.status = models.OrderStatus.PAID
            self.db.commit()
            self.db.refresh(order)
        return payment

    def ship_order(self, order_id: int) -> models.Order:
        order = self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != models.OrderStatus.PAID:
            raise HTTPException(status_code=400, detail="Order must be paid before shipping")
        # Enqueue async shipping task
        ship_order_task.delay(order_id)
        # Return current order (status still PAID) – task will update later
        return order

    def close_order(self, order_id: int) -> models.Order:
        order = self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != models.OrderStatus.SHIPPED:
            raise HTTPException(status_code=400, detail="Order must be shipped before closing")
        return self.order_repo.update_status(order, models.OrderStatus.CLOSED)

# Additional service wrappers for compatibility with routers
class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.order_repo = OrderRepository(db)

    def get_invoice(self, invoice_id: int) -> models.Invoice:
        return self.invoice_repo.db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    def create_invoice(self, order_id: int, invoice_in: schemas.InvoiceCreate) -> models.Invoice:
        # Delegates to OrderService.create_invoice for business rules
        return OrderService(self.db).create_invoice(order_id, invoice_in)

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.order_repo = OrderRepository(db)

    def get_payment(self, payment_id: int) -> models.Payment:
        return self.payment_repo.db.query(models.Payment).filter(models.Payment.id == payment_id).first()

    def create_payment(self, payment_in: schemas.PaymentCreate) -> models.Payment:
        return OrderService(self.db).record_payment(payment_in)

    def verify_payment(self, payment_id: int, success: bool) -> models.Payment:
        # Enqueue verification instead of direct call
        verify_payment_task.delay(payment_id, success)
        # Return payment record (status may still be PENDING)
        return self.db.query(models.Payment).filter(models.Payment.id == payment_id).first()

class ShippingService:
    def __init__(self, db: Session):
        self.db = db
        self.order_service = OrderService(db)

    def ship_order(self, order_id: int) -> models.Order:
        # Enqueue shipping task
        ship_order_task.delay(order_id)
        # Return current order state (still PAID) – task will update to SHIPPED
        return self.db.query(models.Order).filter(models.Order.id == order_id).first()

    def close_order(self, order_id: int) -> models.Order:
    def get_product(self, product_id: int) -> Optional[models.Product]:
        return self.repo.get(product_id)
# --- Additional simple services for customers and products ---
class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CustomerRepository(db)

    def create_customer(self, payload: schemas.CustomerCreate) -> models.Customer:
        customer = models.Customer(
            name=payload.name,
            address=payload.address,
            phone=payload.phone,
            banking_details=payload.banking_details,
            role=payload.role,
        )
        return self.repo.create(customer)

    def get_customer(self, customer_id: int) -> Optional[models.Customer]:
        return self.repo.get(customer_id)

class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductRepository(db)

    def create_product(self, payload: schemas.ProductCreate) -> models.Product:
        product = models.Product(
            description=payload.description,
            base_price=payload.base_price,
            currency=payload.currency,
        )
        return self.repo.create(product)

    def list_products(self, skip: int = 0, limit: int = 100) -> List[models.Product]:
        return self.repo.list(skip, limit)
