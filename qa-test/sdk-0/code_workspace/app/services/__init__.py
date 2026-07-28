"""Service layer – business logic"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List
from fastapi import HTTPException, status
from app.repositories import OrderRepository, ProductRepository, InvoiceRepository, PaymentRepository, CustomerRepository
from app.models.schemas import OrderCreate, InvoiceCreate, PaymentCreate
from app.queue.queue_manager import enqueue_order_task

class OrderService:
    def __init__(self, db):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.product_repo = ProductRepository(db)
        self.customer_repo = CustomerRepository(db)

    async def place_order(self, order_data: OrderCreate):
        # validate customer exists
        cust = await self.customer_repo.get(order_data.customerRef)
        if not cust:
            raise HTTPException(status_code=404, detail="Customer not found")
        # create order
        order = await self.order_repo.create(order_data)
        # enqueue for async processing (e.g., payment, shipping)
        await enqueue_order_task(order.id)
        return order

    async def accept_order(self, order_id: str):
        order = await self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "PLACED":
            raise HTTPException(status_code=409, detail="Order not in PLACED state")
        await self.order_repo.update_status(order_id, "ACCEPTED")
        return await self.order_repo.get(order_id)

    async def get_order(self, order_id: str):
        order = await self.order_repo.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

class InvoiceService:
    def __init__(self, db):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.order_repo = OrderRepository(db)
        self.customer_repo = CustomerRepository(db)

    async def create_invoice(self, data: InvoiceCreate):
        order = await self.order_repo.get(data.orderRef)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "ACCEPTED":
            raise HTTPException(status_code=409, detail="Order not accepted yet")
        # snapshot billing info from customer
        customer = await self.customer_repo.get(order.customer_id)
        billing_info = {"name": customer.name, "address": customer.address}
        # compute due date default
        issue_dt = datetime.strptime(data.issueDate, "%d/%m/%Y")
        due_str = data.dueDate
        if not due_str:
            due_dt = issue_dt + timedelta(days=7)
            due_str = due_dt.strftime("%d/%m/%Y")
        invoice_dict = {
            "order_id": data.orderRef,
            "billing_info": billing_info,
            "total_amount": order.total_amount,
            "issue_date": data.issueDate,
            "due_date": due_str,
            "status": "ISSUED",
        }
        invoice = await self.invoice_repo.create(type('Temp', (), invoice_dict))
        # link invoice to order
        await self.order_repo.update_status(order.id, "INVOICED")
        return invoice

class PaymentService:
    def __init__(self, db):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.order_repo = OrderRepository(db)
        self.invoice_repo = InvoiceRepository(db)

    async def pay_invoice(self, data: PaymentCreate):
        order = await self.order_repo.get(data.orderRef)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "INVOICED":
            raise HTTPException(status_code=409, detail="Order not invoiced")
        invoice = await self.invoice_repo.get(order.invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if data.amount != invoice.total_amount:
            raise HTTPException(status_code=400, detail="Payment amount mismatch")
        payment = await self.payment_repo.create(type('Temp', (), {
            "order_id": order.id,
            "amount": data.amount,
            "method": data.method,
            "status": "PENDING",
        }))
        # Simulate external gateway call with retry (handled in controller)
        return payment
