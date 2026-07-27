import asyncio
from typing import List, Dict
from app.repositories import OrderRepository, ProductRepository, CustomerRepository, PaymentRepository, InvoiceRepository
from app.db.connection_pool import get_engine
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import OrderStatusEnum, PaymentStatusEnum, InvoiceStatusEnum, Order, Payment, Invoice
from datetime import datetime, timedelta

# Simple in-memory async queue for order processing tasks (e.g., background workers)
class QueueManager:
    def __init__(self, maxsize: int = 1000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)

    async def enqueue(self, task: Dict) -> None:
        await self.queue.put(task)

    async def dequeue(self) -> Dict:
        return await self.queue.get()

    def size(self) -> int:
        return self.queue.qsize()

queue_manager = QueueManager()

# Service layer functions
class OrderService:
    @staticmethod
    async def place_order(customer_id: str, line_items: List[Dict]) -> Order:
        async with AsyncSession(get_engine()) as session:
            order = await OrderRepository.create(session, customer_id, line_items)
            # Enqueue background task for further processing (e.g., notification)
            await queue_manager.enqueue({"type": "order_placed", "order_id": order.id})
            return order

    @staticmethod
    async def accept_order(order_id: str) -> None:
        async with AsyncSession(get_engine()) as session:
            await OrderRepository.update_status(session, order_id, OrderStatusEnum.ACCEPTED.value)

    @staticmethod
    async def ship_order(order_id: str) -> None:
        async with AsyncSession(get_engine()) as session:
            await OrderRepository.update_status(session, order_id, OrderStatusEnum.SHIPPED.value)

    @staticmethod
    async def close_order(order_id: str) -> None:
        async with AsyncSession(get_engine()) as session:
            await OrderRepository.update_status(session, order_id, OrderStatusEnum.CLOSED.value)

class PaymentService:
    @staticmethod
    async def record_payment(order_id: str, amount: str, method: str) -> Payment:
        async with AsyncSession(get_engine()) as session:
            payment = await PaymentRepository.create(session, order_id, amount, method)
            return payment

    @staticmethod
    async def verify_payment(payment_id: str) -> None:
        async with AsyncSession(get_engine()) as session:
            await PaymentRepository.update_status(session, payment_id, PaymentStatusEnum.VERIFIED.value)

class InvoiceService:
    @staticmethod
    async def create_invoice(order_id: str, issue_date_str: str, due_date_str: str) -> Invoice:
        async with AsyncSession(get_engine()) as session:
            order = await OrderRepository.get_by_id(session, order_id)
            if not order:
                raise ValueError('Order not found')
            # Snapshot billing info from customer
            customer = await CustomerRepository.get_by_id(session, order.customer_id)
            billing_name = customer.name
            billing_address = customer.address
            # Parse dates
            issue_date = datetime.strptime(issue_date_str, "%d/%m/%Y")
            due_date = datetime.strptime(due_date_str, "%d/%m/%Y")
            invoice = await InvoiceRepository.create(
                session,
                order_id=order_id,
                billing_name=billing_name,
                billing_address=billing_address,
                total_amount=order.total_amount,
                issue_date=issue_date,
                due_date=due_date,
            )
            # Link invoice to order
            await OrderRepository.update_status(session, order_id, OrderStatusEnum.INVOICED.value)
            return invoice
