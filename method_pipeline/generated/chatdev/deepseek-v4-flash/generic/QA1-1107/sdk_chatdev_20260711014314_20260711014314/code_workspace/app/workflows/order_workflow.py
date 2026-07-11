"""
Order workflow orchestrator.
Coordinates the 7-step order lifecycle across multiple services.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import OrderStatus, PaymentStatus, InvoiceStatus, PaymentMethod
from app.models.order import Order
from app.models.payment import Payment
from app.models.invoice import Invoice
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.invoice_service import InvoiceService
from app.schemas.order import OrderCreate
from app.schemas.payment import PaymentCreate
from app.schemas.invoice import InvoiceCreate


class OrderWorkflow:
    """
    Orchestrates the complete order lifecycle:
    1. Customer places order  -> OrderService.create
    2a. Order Staff reviews order -> OrderService.update_status(REVIEW)
    2b. Order Staff accepts order -> OrderService.update_status(ACCEPTED)
    3. Accountant creates invoice -> InvoiceService.create + issue
    4. Customer pays invoice -> PaymentService.create
    5. Accountant verifies payment -> PaymentService.verify_payment
    6. Order Staff ships paid order -> OrderService.update_status(SHIPPED)
    7. Order Staff closes completed order -> OrderService.update_status(CLOSED)
    """

    @staticmethod
    async def place_order(db: AsyncSession, data: OrderCreate) -> Order:
        """Step 1: Customer places an order."""
        return await OrderService.create(db, data)

    @staticmethod
    async def review_order(db: AsyncSession, order_id: str) -> Order:
        """Step 2a: Order Staff reviews an order (PENDING -> REVIEW)."""
        return await OrderService.update_status(db, order_id, OrderStatus.REVIEW)

    @staticmethod
    async def accept_order(db: AsyncSession, order_id: str) -> Order:
        """Step 2b: Order Staff accepts a reviewed order (REVIEW -> ACCEPTED)."""
        return await OrderService.update_status(db, order_id, OrderStatus.ACCEPTED)

    @staticmethod
    async def create_and_issue_invoice(
        db: AsyncSession,
        order_id: str,
        billing_info: Optional[dict] = None,
        issue_date: Optional[date] = None,
        due_date: Optional[date] = None,
    ) -> Invoice:
        """Step 3: Accountant creates and issues an invoice for an accepted order."""
        today = issue_date or date.today()
        due = due_date or (today + timedelta(days=30))
        invoice_data = InvoiceCreate(
            order_id=order_id,
            billing_info=billing_info or {},
            issue_date=today,
            due_date=due,
        )
        invoice = await InvoiceService.create(db, invoice_data)
        # Automatically issue the invoice
        invoice = await InvoiceService.issue_invoice(db, invoice.id)
        # Update order status to INVOICED
        order = await OrderService.update_status(db, order_id, OrderStatus.INVOICED)
        # Set the invoice reference on the order (domain model contract)
        if order:
            order.invoice_ref = invoice.id
        await db.flush()
        return invoice

    @staticmethod
    async def pay_invoice(
        db: AsyncSession,
        order_id: str,
        amount: Decimal,
        method: PaymentMethod,
        transaction_ref: Optional[str] = None,
        currency: str = "USD",
    ) -> Payment:
        """Step 4: Customer pays the invoice.

        Validates that:
        1. The order is in INVOICED status (invoice must be created and issued before payment).
        2. No pending payment already exists for this order (prevents duplicate payment submissions).
        """
        # Validate order exists and is in INVOICED status
        order = await OrderService.get_by_id(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.INVOICED:
            raise ValueError(
                f"Cannot pay for order {order_id} in status {order.status.value}. "
                f"Order must be in INVOICED status."
            )

        # Prevent duplicate payment submissions: check if a pending payment already exists
        existing_payments = await PaymentService.get_by_order(db, order_id)
        for p in existing_payments:
            if p.status == PaymentStatus.PENDING:
                raise ValueError(
                    f"A pending payment {p.id} already exists for order {order_id}. "
                    f"Please wait for verification or cancel the existing payment."
                )

        payment_data = PaymentCreate(
            order_id=order_id,
            amount=amount,
            method=method,
            transaction_ref=transaction_ref,
            currency=currency,
        )
        return await PaymentService.create(db, payment_data)

    @staticmethod
    async def verify_payment(db: AsyncSession, payment_id: str) -> Payment:
        """Step 5: Accountant verifies the payment.

        Validates that:
        1. The payment exists and is in PENDING status.
        2. The order is in INVOICED status (payment must follow invoice creation).
        3. The payment amount matches the invoice total.
        Then marks the payment as completed, updates order to PAID, and marks invoice as paid.
        """
        payment = await PaymentService.get_by_id(db, payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        # Validate payment is still pending (prevents re-verification)
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(
                f"Payment {payment_id} is already in status {payment.status.value}. "
                f"Only PENDING payments can be verified."
            )

        # Validate order exists and is in INVOICED status
        order = await OrderService.get_by_id(db, payment.order_id)
        if not order:
            raise ValueError(f"Order {payment.order_id} not found")
        if order.status != OrderStatus.INVOICED:
            raise ValueError(
                f"Cannot verify payment for order {payment.order_id} in status "
                f"{order.status.value}. Order must be in INVOICED status."
            )

        # Validate payment amount matches invoice total
        invoices = await InvoiceService.get_by_order(db, payment.order_id)
        if not invoices:
            raise ValueError(f"No invoices found for order {payment.order_id}")
        latest_invoice = invoices[0]
        if payment.amount != latest_invoice.total_amount:
            raise ValueError(
                f"Payment amount {payment.amount} does not match invoice total "
                f"{latest_invoice.total_amount} for invoice {latest_invoice.id}"
            )

        # Mark payment as completed
        payment = await PaymentService.verify_payment(db, payment_id)
        # Update order status to PAID
        await OrderService.update_status(db, payment.order_id, OrderStatus.PAID)
        # Mark invoice as paid
        for inv in invoices:
            if inv.status in (InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
                await InvoiceService.mark_paid(db, inv.id)
        return payment

    @staticmethod
    async def ship_order(db: AsyncSession, order_id: str) -> Order:
        """Step 6: Order Staff ships the paid order."""
        return await OrderService.update_status(db, order_id, OrderStatus.SHIPPED)

    @staticmethod
    async def close_order(db: AsyncSession, order_id: str) -> Order:
        """Step 7: Order Staff closes the completed order."""
        return await OrderService.update_status(db, order_id, OrderStatus.CLOSED)
