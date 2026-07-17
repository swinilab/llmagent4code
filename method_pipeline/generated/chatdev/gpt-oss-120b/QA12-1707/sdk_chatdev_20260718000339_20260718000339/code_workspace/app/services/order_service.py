from datetime import datetime, timedelta

from fastapi import HTTPException

from sqlmodel import Session, select

from ..models import (
    Order,
    OrderLineItem,
    OrderStatus,
    Customer,
    Product,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
)
from .product_service import ProductService
from ..config import settings


class OrderService:
    @staticmethod
    def create_order(
        session: Session,
        customer_id: int,
        items: List[dict],  # each dict: product_id, quantity
    ) -> Order:
        """Create a new order atomically, reducing stock and persisting all data.
        The entire operation runs within a single transaction so that any failure
        rolls back all changes, preserving inventory consistency.
        """
        with session.begin():
            customer = session.get(Customer, customer_id)
            if not customer:
                raise ValueError("Customer not found")

            order = Order(customer_id=customer_id, status=OrderStatus.PENDING)
            session.add(order)
            session.flush()

            line_items: List[OrderLineItem] = []
            for item in items:
                product = ProductService.get_product(session, item["product_id"])
                if not product:
                    raise ValueError(f"Product {item['product_id']} not found")
                if product.quantity < item["quantity"]:
                    raise ValueError(f"Insufficient stock for product {product.id}")
                ProductService.reduce_stock(session, product.id, item["quantity"])
                line = OrderLineItem(
                    order_id=order.id,
    def create_invoice(session: Session, order_id: int, billing_info: str, due_in_days: int = 30) -> Invoice:
        """Accountant creates an invoice for an accepted order."""
        # Graceful degradation: check feature toggle
        if not settings.ENABLE_INVOICE_FEATURE:
            raise HTTPException(
                status_code=503,
                detail="Invoice feature temporarily disabled for graceful degradation.",
            )
        with session.begin():
            order = session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.ACCEPTED:
                raise ValueError("Invoice can only be created for accepted orders")
            due_date = datetime.utcnow() + timedelta(days=due_in_days)
            invoice = Invoice(
                order_id=order.id,
                billing_info=billing_info,
                amount=order.total_amount,
                due_date=due_date,
                status=InvoiceStatus.ISSUED,
            )
            session.add(invoice)
            # link and update order status
            order.status = OrderStatus.INVOICED
            order.updated_at = datetime.utcnow()
            session.add(order)
        session.refresh(invoice)
        return invoice
    def create_invoice(session: Session, order_id: int, billing_info: str) -> Invoice:
        """Accountant creates an invoice for an accepted order."""
        # Graceful degradation: check feature toggle
        if not settings.ENABLE_INVOICE_FEATURE:
            raise HTTPException(
                status_code=503,
                detail="Invoice feature temporarily disabled for graceful degradation.",
            )
        with session.begin():
            order = session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.ACCEPTED:
                raise ValueError("Invoice can only be created for accepted orders")
            invoice = Invoice(
                order_id=order.id,
                billing_info=billing_info,
                amount=order.total_amount,
                status=InvoiceStatus.ISSUED,
            )
            session.add(invoice)
            # link and update order status
            order.status = OrderStatus.INVOICED
            order.updated_at = datetime.utcnow()
            session.add(order)
        session.refresh(invoice)
        return invoice

    @staticmethod
    def record_payment(session: Session, order_id: int, amount: float, method: str) -> Payment:
        """Record payment for an invoiced order and mark order as PAID.
        Assumes payment is successful; status set to COMPLETED.
        """
        with session.begin():
            order = session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.INVOICED:
                raise ValueError("Payment can only be recorded for invoiced orders")
            if amount < order.total_amount:
                raise ValueError("Paid amount is less than order total")
            payment = Payment(
                order_id=order.id,
                amount=amount,
                method=method,
                status=PaymentStatus.COMPLETED,
            )
            session.add(payment)
            order.status = OrderStatus.PAID
            order.updated_at = datetime.utcnow()
            session.add(order)
        session.refresh(payment)
        return payment

    @staticmethod
    def ship_order(session: Session, order_id: int) -> Order:
        """Mark a paid order as shipped."""
        # Graceful degradation: check shipping feature toggle
        if not settings.ENABLE_SHIPPING_FEATURE:
            raise HTTPException(
                status_code=503,
                detail="Shipping feature temporarily disabled for graceful degradation.",
            )
        with session.begin():
            order = session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.PAID:
                raise ValueError("Only paid orders can be shipped")
            order.status = OrderStatus.SHIPPED
            order.updated_at = datetime.utcnow()
            session.add(order)
        session.refresh(order)
        return order

    @staticmethod
    def close_order(session: Session, order_id: int) -> Order:
        """Close a shipped order, finalizing the lifecycle."""
        with session.begin():
            order = session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.SHIPPED:
                raise ValueError("Only shipped orders can be closed")
            order.status = OrderStatus.CLOSED
            order.updated_at = datetime.utcnow()
            session.add(order)
        session.refresh(order)
        return order

    @staticmethod
    def get_order(session: Session, order_id: int) -> Optional[Order]:
        """Retrieve an order by ID, returning None if not found."""
        return session.get(Order, order_id)
