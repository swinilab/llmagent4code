"""
Payment service – handles payment creation and verification.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from oms.models.entities import OrderModel, PaymentModel
from oms.models.enums import InvoiceStatus, OrderStatus, PaymentMethod, PaymentStatus
from oms.repositories.invoice_repo import InvoiceRepository
from oms.repositories.order_repo import OrderRepository
from oms.repositories.payment_repo import PaymentRepository
from oms.schemas.payment import PaymentCreate

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PaymentRepository(db)
        self.order_repo = OrderRepository(db)
        self.invoice_repo = InvoiceRepository(db)

    def create_payment(self, data: PaymentCreate) -> PaymentModel:
        """Record a payment attempt. Critical operation."""
        order = self.db.query(OrderModel).filter(
            OrderModel.id == data.order_id
        ).first()
        if not order:
            raise ValueError(f"Order {data.order_id} not found")
        if order.status != OrderStatus.INVOICED:
            raise ValueError(
                f"Cannot pay order in status {order.status.value}"
            )

        # Validate payment amount matches order total
        if data.amount != order.total_amount:
            raise ValueError(
                f"Payment amount {data.amount} does not match order total {order.total_amount}"
            )

        # Validate payment currency matches order currency (Fix 3)
        if data.currency != order.currency:
            raise ValueError(
                f"Payment currency {data.currency} does not match "
                f"order currency {order.currency}"
            )

        payment = PaymentModel(
            order_id=data.order_id,
            amount=data.amount,
            currency=data.currency,
            method=data.method,
            status=PaymentStatus.PENDING,
        )
        self.repo.create(payment)

        # Outbox
        self.repo.write_outbox(
            aggregate_type="payment",
            aggregate_id=payment.id,
            event_type="payment.created",
            payload={
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "amount": payment.amount,
            },
        )
        self.db.commit()
        logger.info("Payment %s created for order %s", payment.id, data.order_id)
        return payment

    def verify_payment(self, payment_id: str) -> PaymentModel:
        """
        Mark a payment as COMPLETED and transition the order to PAID.
        Also marks the associated invoice as PAID.
        Critical operation.

        Uses a single fetch of the order after the payment update to avoid
        TOCTOU (Time-of-Check-Time-of-Use) issues. The order status is
        validated atomically via optimistic locking on the update itself.
        """
        payment = self.repo.get(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment already {payment.status.value}")

        # Fetch the order once for the initial status check
        order_before = self.order_repo.get(payment.order_id)
        if not order_before:
            raise ValueError(f"Order {payment.order_id} not found")
        if order_before.status != OrderStatus.INVOICED:
            raise ValueError(
                f"Order {payment.order_id} is in status {order_before.status.value}, "
                f"expected INVOICED"
            )

        # Update payment with optimistic lock
        updated = self.repo.update_with_optimistic_lock(
            payment_id,
            {
                "status": PaymentStatus.COMPLETED,
                "paid_at": datetime.now(timezone.utc),
            },
            payment.version,
        )
        if updated is None:
            raise ValueError(f"Concurrent modification on payment {payment_id}")

        # Re-fetch the order AFTER the payment update to get the latest state.
        # This is necessary because another transaction may have modified the
        # order between our initial check and the payment update. The optimistic
        # lock on the order update below will catch any concurrent modifications.
        order_after = self.order_repo.get(updated.order_id)
        if order_after and order_after.status == OrderStatus.INVOICED:
            updated_order = self.order_repo.update_with_optimistic_lock(
                order_after.id,
                {"status": OrderStatus.PAID},
                order_after.version,
            )
            if updated_order is None:
                raise ValueError(
                    f"Concurrent modification on order {order_after.id} during payment verification"
                )

            # Also mark the associated invoice as PAID
            if updated_order.invoice_ref:
                invoice = self.invoice_repo.get(updated_order.invoice_ref)
                if invoice and invoice.status == InvoiceStatus.ISSUED:
                    updated_invoice = self.invoice_repo.update_with_optimistic_lock(
                        invoice.id,
                        {"status": InvoiceStatus.PAID},
                        invoice.version,
                    )
                    if updated_invoice is None:
                        raise ValueError(
                            f"Concurrent modification on invoice {invoice.id} "
                            f"during payment verification"
                        )

                    # Outbox for invoice status transition
                    self.repo.write_outbox(
                        aggregate_type="invoice",
                        aggregate_id=invoice.id,
                        event_type="invoice.paid",
                        payload={
                            "invoice_id": invoice.id,
                            "order_id": updated.order_id,
                            "previous_status": InvoiceStatus.ISSUED.value,
                            "new_status": InvoiceStatus.PAID.value,
                        },
                    )

            # Outbox for order status transition
            self.repo.write_outbox(
                aggregate_type="order",
                aggregate_id=updated.order_id,
                event_type="order.paid",
                payload={
                    "order_id": updated.order_id,
                    "previous_status": OrderStatus.INVOICED.value,
                    "new_status": OrderStatus.PAID.value,
                },
            )

        # Outbox for payment
        self.repo.write_outbox(
            aggregate_type="payment",
            aggregate_id=updated.id,
            event_type="payment.verified",
            payload={
                "payment_id": updated.id,
                "order_id": updated.order_id,
                "status": "COMPLETED",
            },
        )
        self.db.commit()
        logger.info("Payment %s verified for order %s", payment_id, updated.order_id)
        return updated

    def get_payment(self, payment_id: str) -> Optional[PaymentModel]:
        return self.repo.get(payment_id)

    def list_by_order(self, order_id: str) -> List[PaymentModel]:
        return self.repo.get_by_order(order_id)
