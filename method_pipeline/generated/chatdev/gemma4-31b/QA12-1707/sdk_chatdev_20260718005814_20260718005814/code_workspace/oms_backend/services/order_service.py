"""
Business logic orchestration for the Order Management System.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from oms_backend.database.db import OrderDB, OrderItemDB, ProductDB, CustomerDB, PaymentDB, InvoiceDB
from oms_backend.models.schemas import OrderCreate, OrderStatus, PaymentStatus, InvoiceStatus, CustomerCreate, InvoiceCreate, PaymentCreate
from oms_backend.utils.resilience import resilience_retry, circuit_breaker_timeout
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

class OrderService:
    @staticmethod
    @resilience_retry()
    @circuit_breaker_timeout(timeout_seconds=10.0)
    async def create_order(db: AsyncSession, order_data: OrderCreate):
        # Optimization: Batch fetch all products to avoid N+1 query problem (NFR 1.1)
        product_ids = [item.product_id for item in order_data.items]
        res = await db.execute(select(ProductDB).where(ProductDB.id.in_(product_ids)))
        products = {p.id: p for p in res.scalars().all()}
        
        total = 0.0
        items_to_create = []
        for item in order_data.items:
            product = products.get(item.product_id)
            if not product:
                raise ValueError(f"Product with id {item.product_id} not found")
            
            total += product.base_price * item.quantity
            items_to_create.append(OrderItemDB(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.base_price
            ))
        
        new_order = OrderDB(
            customer_id=order_data.customer_id,
            status=OrderStatus.PENDING,
            total_amount=total,
            created_at=datetime.now()
        )
        db.add(new_order)
        await db.flush() # Get order ID without committing transaction
        
        for item in items_to_create:
            item.order_id = new_order.id
            db.add(item)
            
        await db.commit() # Single atomic commit for order and items
        await db.refresh(new_order)
        return new_order

    @staticmethod
    @resilience_retry()
    @circuit_breaker_timeout(timeout_seconds=5.0)
    async def accept_order(db: AsyncSession, order_id: int):
        logger.info(f"Action: OrderStaff accepting order {order_id}")
        res = await db.execute(select(OrderDB).where(OrderDB.id == order_id))
        order = res.scalar_one_or_none()
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only PENDING orders can be accepted")
        
        order.status = OrderStatus.ACCEPTED
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    @resilience_retry()
    @circuit_breaker_timeout(timeout_seconds=5.0)
    async def create_invoice(db: AsyncSession, invoice_data: InvoiceCreate):
        logger.info(f"Action: Accountant creating invoice for order {invoice_data.order_id}")
        res = await db.execute(select(OrderDB).where(OrderDB.id == invoice_data.order_id))
        order = res.scalar_one_or_none()
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError("Order must be ACCEPTED before invoicing")
        
        invoice = InvoiceDB(
            order_id=order.id,
            billing_info=invoice_data.billing_info,
            amount=order.total_amount,
            issue_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            status=InvoiceStatus.UNPAID
        )
        db.add(invoice)
        
        order.status = OrderStatus.INVOICED
        
        # Single commit for both entities to ensure atomicity (NFR 2.3)
        await db.commit()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    @resilience_retry()
    @circuit_breaker_timeout(timeout_seconds=5.0)
    async def process_payment(db: AsyncSession, payment_data: PaymentCreate):
        logger.info(f"Action: Customer paying invoice {payment_data.invoice_id}")
        res = await db.execute(select(InvoiceDB).where(InvoiceDB.id == payment_data.invoice_id))
        invoice = res.scalar_one_or_none()
        if not invoice:
            raise ValueError("Invoice not found")
        
        payment = PaymentDB(
            invoice_id=invoice.id,
            amount=payment_data.amount,
            status=PaymentStatus.COMPLETED,
            timestamp=datetime.now(),
            method=payment_data.method
        )
        db.add(payment)
        invoice.status = InvoiceStatus.PAID
        
        await db.commit() # Single commit for payment and invoice status update
        await db.refresh(payment)
        return payment

    @staticmethod
    @resilience_retry()
    @circuit_breaker_timeout(timeout_seconds=5.0)
    async def verify_payment(db: AsyncSession, order_id: int):
        logger.info(f"Action: Accountant verifying payment for order {order_id}")
        res = await db.execute(select(OrderDB).where(OrderDB.id == order_id))
        order = res.scalar_one_or_none()
        if not order:
            raise ValueError("Order not found")
        
        res_inv = await db.execute(select(InvoiceDB).where(InvoiceDB.order_id == order_id))
        invoice = res_inv.scalar_one_or_none()
        if not invoice or invoice.status != InvoiceStatus.PAID:
            raise ValueError("Invoice not paid yet")
        
        # Strict Workflow Validation: Ensure a Payment record exists
        res_pay = await db.execute(select(PaymentDB).where(PaymentDB.invoice_id == invoice.id))
        payment = res_pay.scalar_one_or_none()
        if not payment or payment.status != PaymentStatus.COMPLETED:
            raise ValueError("No completed payment record found for this invoice")
        
        order.status = OrderStatus.PAID
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    @resilience_retry()
    @circuit_breaker_timeout(timeout_seconds=5.0)
    async def ship_order(db: AsyncSession, order_id: int):
        logger.info(f"Action: OrderStaff shipping order {order_id}")
        res = await db.execute(select(OrderDB).where(OrderDB.id == order_id))
        order = res.scalar_one_or_none()
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PAID:
            raise ValueError("Order must be PAID before shipping")
        
        order.status = OrderStatus.SHIPPED
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    @resilience_retry()
    @circuit_breaker_timeout(timeout_seconds=5.0)
    async def close_order(db: AsyncSession, order_id: int):
        logger.info(f"Action: OrderStaff closing order {order_id}")
        res = await db.execute(select(OrderDB).where(OrderDB.id == order_id))
        order = res.scalar_one_or_none()
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.SHIPPED:
            raise ValueError("Order must be SHIPPED before closing")
        
        order.status = OrderStatus.CLOSED
        await db.commit()
        await db.refresh(order)
        return order

class ProductService:
    @staticmethod
    @resilience_retry()
    async def get_all(db: AsyncSession):
        res = await db.execute(select(ProductDB))
        return res.scalars().all()

class CustomerService:
    @staticmethod
    @resilience_retry()
    async def create_customer(db: AsyncSession, customer_data: CustomerCreate):
        customer = CustomerDB(
            name=customer_data.name,
            address=customer_data.address,
            phone=customer_data.phone,
            banking_details=customer_data.banking_details,
            role=customer_data.role
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer
