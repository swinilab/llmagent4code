"""
Workflow orchestration service.
Coordinates the full order lifecycle: order → accept → invoice → pay → ship → close.
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.models import (
    Order as OrderDomain,
    Payment as PaymentDomain,
    Invoice as InvoiceDomain,
    Customer as CustomerDomain,
)
from oms.domain.enums import OrderStatus, PaymentMethod, PaymentStatus, InvoiceStatus
from oms.domain.errors import BusinessRuleViolationError, EntityNotFoundError
from oms.application.services import (
    CustomerService,
    ProductService,
    OrderService,
    PaymentService,
    InvoiceService,
)
from oms.infrastructure.task_queue import TaskQueue
from oms.infrastructure.logging import get_logger

logger = get_logger(__name__)


class WorkflowService:
    """
    Orchestrates the complete order workflow.
    Each method corresponds to a step in the user workflow.
    """

    def __init__(
        self,
        customer_service: CustomerService,
        product_service: ProductService,
        order_service: OrderService,
        payment_service: PaymentService,
        invoice_service: InvoiceService,
        task_queue: TaskQueue,
    ):
        self._customer_service = customer_service
        self._product_service = product_service
        self._order_service = order_service
        self._payment_service = payment_service
        self._invoice_service = invoice_service
        self._task_queue = task_queue

    async def place_order(
        self,
        session: AsyncSession,
        customer_id: str,
        line_items_data: list[dict],
    ) -> OrderDomain:
        """
        Step 1: Customer places order.
        This is on the critical path for checkout (NFR 1.1).
        """
        # Verify customer exists
        customer = await self._customer_service.get_customer(session, customer_id)
        # Create the order
        order = await self._order_service.create_order(session, customer_id, line_items_data)
        logger.info("Order placed", extra={"order_id": order.id, "customer_id": customer_id})
        return order

    async def accept_order(
        self, session: AsyncSession, order_id: str, expected_version: int
    ) -> OrderDomain:
        """
        Step 2: Order Staff reviews & accepts.
        Back-office step, relaxed latency budget.
        """
        order = await self._order_service.transition_order(
            session, order_id, OrderStatus.ACCEPTED, expected_version
        )
        logger.info("Order accepted", extra={"order_id": order_id})
        return order

    async def create_invoice_for_order(
        self,
        session: AsyncSession,
        order_id: str,
        expected_version: int,
        billing_name: Optional[str] = None,
        billing_address: Optional[str] = None,
    ) -> InvoiceDomain:
        """
        Step 3: Accountant creates invoice for accepted order.
        Back-office step. Enqueues async task for notification.
        """
        # Get the order
        order = await self._order_service.get_order(session, order_id)
        if order.status != OrderStatus.ACCEPTED:
            raise BusinessRuleViolationError(
                f"Cannot create invoice for order in status {order.status.value}"
            )

        # Get customer for billing info
        customer = await self._customer_service.get_customer(session, order.customer_id)

        # Create invoice
        invoice = await self._invoice_service.create_invoice(
            session,
            order_id=order_id,
            billing_name=billing_name or customer.name,
            billing_address=billing_address or customer.address,
            total_amount=order.total_amount,
            currency=order.currency,
        )

        # Issue the invoice
        invoice = await self._invoice_service.issue_invoice(session, invoice.id)

        # Update order to INVOICED
        order = await self._order_service.transition_order(
            session, order_id, OrderStatus.INVOICED, expected_version
        )

        # Update order's invoice ref using the injected order service
        await self._order_service.update_invoice_ref(session, order_id, invoice.id)

        # Enqueue async notification task
        await self._task_queue.enqueue(
            "oms.application.tasks.send_notification_task",
            customer_id=order.customer_id,
            message=f"Invoice {invoice.id} created for order {order_id}",
        )

        logger.info("Invoice created", extra={"invoice_id": invoice.id, "order_id": order_id})
        return invoice

    async def pay_invoice(
        self,
        session: AsyncSession,
        order_id: str,
        amount: Decimal,
        currency: str = "USD",
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
    ) -> PaymentDomain:
        """
        Step 4: Customer pays invoice.
        This is on the critical path for checkout (NFR 1.1).
        The expected_version is not needed here because payment creation
        does not transition the order; the order transitions to PAID in verify_payment.
        """
        # Verify order exists and is in INVOICED state
        order = await self._order_service.get_order(session, order_id)
        if order.status != OrderStatus.INVOICED:
            raise BusinessRuleViolationError(
                f"Cannot pay order in status {order.status.value}"
            )

        # Create payment record
        payment = await self._payment_service.create_payment(
            session, order_id, amount, currency, method
        )

        logger.info("Payment created", extra={"payment_id": payment.id, "order_id": order_id})
        return payment

    async def verify_payment(
        self,
        session: AsyncSession,
        payment_id: str,
        order_id: str,
        expected_version: int,
    ) -> OrderDomain:
        """
        Step 5: Accountant verifies payment.
        Back-office step.
        Verifies that the payment belongs to the specified order.
        Idempotent: if the payment is already COMPLETED, returns the current order.
        """
        # Verify payment exists and belongs to the specified order
        payment = await self._payment_service.get_payment(session, payment_id)
        if payment.order_id != order_id:
            raise BusinessRuleViolationError(
                f"Payment {payment_id} does not belong to order {order_id}"
            )

        # Idempotency guard: skip if already completed
        if payment.status == PaymentStatus.COMPLETED:
            logger.info(
                "Payment already verified, skipping",
                extra={"payment_id": payment_id, "order_id": order_id},
            )
            return await self._order_service.get_order(session, order_id)

        # Mark payment as completed
        payment = await self._payment_service.verify_payment(session, payment_id)

        # Mark invoice as paid
        invoice = await self._invoice_service.get_invoice_by_order(session, order_id)
        if invoice:
            await self._invoice_service.mark_paid(session, invoice.id)

        # Transition order to PAID
        order = await self._order_service.transition_order(
            session, order_id, OrderStatus.PAID, expected_version
        )

        logger.info("Payment verified", extra={"payment_id": payment_id, "order_id": order_id})
        return order

    async def ship_order(
        self,
        session: AsyncSession,
        order_id: str,
        expected_version: int,
    ) -> OrderDomain:
        """
        Step 6: Order Staff ships paid order.
        Back-office step.
        """
        order = await self._order_service.transition_order(
            session, order_id, OrderStatus.SHIPPED, expected_version
        )
        logger.info("Order shipped", extra={"order_id": order_id})
        return order

    async def close_order(
        self,
        session: AsyncSession,
        order_id: str,
        expected_version: int,
    ) -> OrderDomain:
        """
        Step 7: Order Staff closes completed order.
        Back-office step.
        """
        order = await self._order_service.transition_order(
            session, order_id, OrderStatus.CLOSED, expected_version
        )
        logger.info("Order closed", extra={"order_id": order_id})
        return order

    async def cancel_order(
        self,
        session: AsyncSession,
        order_id: str,
        expected_version: int,
    ) -> OrderDomain:
        """
        Cancel an order from any pre-SHIPPED state.
        """
        order = await self._order_service.transition_order(
            session, order_id, OrderStatus.CANCELLED, expected_version
        )
        logger.info("Order cancelled", extra={"order_id": order_id})
        return order

    async def transition_order(
        self,
        session: AsyncSession,
        order_id: str,
        target_status: OrderStatus,
        expected_version: int,
    ) -> OrderDomain:
        """
        Generic order status transition.
        Used by the /orders/{order_id}/transition endpoint.
        """
        return await self._order_service.transition_order(
            session, order_id, target_status, expected_version
        )
