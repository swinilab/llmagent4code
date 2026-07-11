"""
Payment service: handles payment processing and verification.

Criticality: CORE (NFR 2.1) — payment is part of the checkout flow.
Recovery: Retry on transient DB errors (NFR 2.2); idempotency key prevents
duplicate charges.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbox import OutboxRepository
from app.adapters.repositories import InvoiceRepository, OrderRepository, PaymentRepository
from app.domain.enums import InvoiceStatus, OrderStatus, PaymentMethod, PaymentStatus
from app.domain.models import Payment
from app.domain.schemas import PaymentCreate
from app.domain.state_machine import TransitionEvent
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class PaymentService:
    """Encapsulates payment business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payment_repo = PaymentRepository(session)
        self._order_repo = OrderRepository(session)
        self._invoice_repo = InvoiceRepository(session)
        self._outbox_repo = OutboxRepository(session)

    async def process_payment(self, data: PaymentCreate) -> Payment:
        """
        Process a payment for an order.

        This implements workflow step 4 (Customer pays invoice).
        Idempotency is enforced via the idempotency_key.

        Delegates the order state transition (INVOICED -> PAID) to
        OrderService.transition_order(), which enforces the domain state
        machine via apply_transition() — ensuring the state machine
        remains the single source of truth for all transitions (see ADR-003).

        After the order transitions to PAID, the associated invoice status
        is also updated to PAID (fixing the dead-code issue where
        InvoiceRepository.update_status() was never called).
        """
        # Check idempotency
        existing = await self._payment_repo.get_by_idempotency_key(data.idempotency_key)
        if existing is not None:
            logger.info(
                "Idempotent payment request (key=%s), returning existing payment %s",
                data.idempotency_key,
                existing.id,
            )
            return existing

        # Validate order exists and is in INVOICED state
        order = await self._order_repo.get(data.order_id)
        if order is None:
            raise ValueError(f"Order {data.order_id} not found")
        if order.status != OrderStatus.INVOICED:
            raise ValueError(
                f"Order {data.order_id} is in status '{order.status.value}', "
                f"expected 'INVOICED'. Payment can only be processed for "
                f"invoiced orders."
            )

        # Validate payment amount matches order total (state-machine guard:
        # "Payment completed; amount match" for INVOICED -> PAID transition)
        if abs(data.amount - order.total_amount) > 0.01:
            raise ValueError(
                f"Payment amount {data.amount} does not match order total "
                f"{order.total_amount} for order {data.order_id}. "
                f"Difference exceeds tolerance of 0.01."
            )

        # Create payment record
        payment = Payment(
            order_id=data.order_id,
            amount=data.amount,
            method=data.method,
            status=PaymentStatus.COMPLETED,
            idempotency_key=data.idempotency_key,
        )
        payment = await self._payment_repo.create(payment)

        # Delegate the state transition to OrderService, which calls
        # apply_transition() and persists the new status atomically.
        order_service = OrderService(self._session)
        try:
            await order_service.transition_order(
                order_id=data.order_id,
                event=TransitionEvent.PAY,
            )
        except ValueError as exc:
            # If the transition fails (e.g., optimistic lock conflict),
            # the payment was already created — manual intervention needed.
            logger.error(
                "Payment %s created but order %s transition failed: %s",
                payment.id,
                data.order_id,
                exc,
            )
            raise

        # Update the associated invoice status to PAID (NFR 2.3 state preservation).
        # This ensures the invoice lifecycle matches the order lifecycle.
        invoices = await self._invoice_repo.get_by_order(data.order_id)
        for inv in invoices:
            if inv.status != InvoiceStatus.PAID:
                updated_inv = await self._invoice_repo.update_status(
                    invoice_id=inv.id,
                    new_status=InvoiceStatus.PAID,
                    current_version=inv.version,
                )
                if updated_inv is None:
                    logger.warning(
                        "Optimistic lock conflict updating invoice %s status to PAID",
                        inv.id,
                    )
                else:
                    logger.info(
                        "Invoice %s status updated to PAID for order %s",
                        inv.id,
                        data.order_id,
                    )

        logger.info(
            "Payment %s processed for order %s (amount=%.2f)",
            payment.id,
            data.order_id,
            data.amount,
        )
        return payment

    async def verify_payment(self, payment_id: uuid.UUID) -> Payment | None:
        """
        Verify a payment (workflow step 5 — Accountant verifies payment).

        In a real system, this would check with the payment gateway.
        Here we simply confirm the payment exists and is completed.
        """
        payment = await self._payment_repo.get(payment_id)
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError(f"Payment {payment_id} is not completed")
        return payment

    async def get_payment(self, payment_id: uuid.UUID) -> Payment | None:
        return await self._payment_repo.get(payment_id)

    async def get_payments_by_order(self, order_id: uuid.UUID) -> list[Payment]:
        return list(await self._payment_repo.get_by_order(order_id))
