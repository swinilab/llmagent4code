"""Service layer: orchestrates business rules and cross‑cutting concerns.
All services receive a DB session (provided by FastAPI dependency) and use repositories.
"""
from sqlalchemy.orm import Session
from typing import List
from models import Customer, Product, Order, OrderLineItem, Payment, Invoice, OrderStatusEnum, PaymentStatusEnum, InvoiceStatusEnum
from repositories import (
    CustomerRepository,
    ProductRepository,
    OrderRepository,
    OrderLineItemRepository,
    PaymentRepository,
    InvoiceRepository,
)
from datetime import datetime, timedelta

# Customer Service
class CustomerService:
    def __init__(self, db: Session):
        self.repo = CustomerRepository(db)

    def create_customer(self, data: dict) -> Customer:
        cust = Customer(**data)
        return self.repo.create(cust)

    def get_customer(self, cust_id: int) -> Customer:
        return self.repo.get(cust_id)

# Product Service
class ProductService:
    def __init__(self, db: Session):
        self.repo = ProductRepository(db)

    def create_product(self, data: dict) -> Product:
        prod = Product(**data)
        return self.repo.create(prod)

    def get_product(self, prod_id: int) -> Product:
        return self.repo.get(prod_id)

# Order Service – core workflow orchestration
class OrderService:
    def __init__(self, db: Session):
        self.order_repo = OrderRepository(db)
        self.item_repo = OrderLineItemRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.product_repo = ProductRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.invoice_repo = InvoiceRepository(db)

    def place_order(self, customer_id: int, line_items: List[dict]) -> Order:
        # Validate customer exists
        customer = self.customer_repo.get(customer_id)
        if not customer:
            raise ValueError("Customer not found")
        # Create order
        order = Order(customer_id=customer_id, status=OrderStatusEnum.CREATED)
        order = self.order_repo.create(order)
        # Create line items with current product price snapshot
        items = []
        for li in line_items:
            product = self.product_repo.get(li["product_id"])
            if not product:
                raise ValueError(f"Product {li['product_id']} not found")
            item = OrderLineItem(
                order_id=order.id,
                product_id=product.id,
                quantity=li["quantity"],
                unit_price=product.price,
            )
            items.append(item)
        self.item_repo.bulk_create(items)
        # Refresh order to include items
        order = self.order_repo.get(order.id)
        return order

    def review_order(self, order_id: int, accept: bool) -> Order:
        order = self.order_repo.get(order_id)
        if not order:
            raise ValueError("Order not found")
        new_status = OrderStatusEnum.ACCEPTED if accept else OrderStatusEnum.CANCELLED
        return self.order_repo.update_status(order, new_status)

    def create_invoice(self, order_id: int, billing_info: str, due_in_days: int = 30) -> Invoice:
        order = self.order_repo.get(order_id)
        if not order or order.status != OrderStatusEnum.ACCEPTED:
            raise ValueError("Order must be accepted before invoicing")
        # Calculate total amount
        total = sum(item.unit_price * item.quantity for item in order.line_items)
        invoice = Invoice(
            order_id=order.id,
            billing_info=billing_info,
            amount=total,
            due_date=datetime.utcnow() + timedelta(days=due_in_days),
            status=InvoiceStatusEnum.ISSUED,
        )
        invoice = self.invoice_repo.create(invoice)
        # Update order status
        self.order_repo.update_status(order, OrderStatusEnum.INVOICED)
        return invoice

    def record_payment(self, order_id: int, method: str, amount: float) -> Payment:
        order = self.order_repo.get(order_id)
        if not order or order.status != OrderStatusEnum.INVOICED:
            raise ValueError("Order must be invoiced before payment")
        payment = Payment(
            order_id=order.id,
            amount=amount,
            method=method,
            status=PaymentStatusEnum.COMPLETED,
        )
        payment = self.payment_repo.create(payment)
        # Update order status
        self.order_repo.update_status(order, OrderStatusEnum.PAID)
        # Also mark invoice as paid
        invoice = self.invoice_repo.get_by_order(order.id)
        if invoice:
            invoice.status = InvoiceStatusEnum.PAID
            self.invoice_repo.db.commit()
        return payment

    def ship_order(self, order_id: int) -> Order:
        order = self.order_repo.get(order_id)
        if not order or order.status != OrderStatusEnum.PAID:
            raise ValueError("Order must be paid before shipping")
        return self.order_repo.update_status(order, OrderStatusEnum.SHIPPED)

    def close_order(self, order_id: int) -> Order:
        order = self.order_repo.get(order_id)
        if not order or order.status != OrderStatusEnum.SHIPPED:
            raise ValueError("Order must be shipped before closure")
        return self.order_repo.update_status(order, OrderStatusEnum.CLOSED)
