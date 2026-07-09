"""
Payment service — handles payment processing and verification.

The workflow is:
  1. Customer pays invoice → process_payment creates a PENDING payment
     (order stays INVOICED).
  2. Accountant verifies payment → verify_payment sets payment to COMPLETED
     and transitions the order to PAID.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.domain.enums import OrderStatus, PaymentStatus
from app.domain.exceptions import (
    DomainError,
    EntityNotFound,
    InvalidOrderStateTransition,
    OptimisticLockError,
    PaymentAlreadyProcessed,
)
from app.domain.models import Order, Payment
from app.domain.schemas import PaymentCreate, PaymentVerification
from app.infrastructure.queue import publish_message
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payment_repo = PaymentRepository(session)
        self._order_repo = OrderRepository(session)

    async def process_payment(self, data: PaymentCreate) -> Payment:
        """Process a payment for an order (hot path — checkout journey).

        Creates a PENDING payment record. The order remains INVOICED until
        the Accountant verifies the payment via verify_payment().
        """
        order = await self._order_repo.get_with_items_or_fail(data.order_id)

        # Optimistic lock check
        if order.version != data.version:
            raise OptimisticLockError()

        # Order must be INVOICED to accept payment
        if order.status != OrderStatus.INVOICED:
            raise InvalidOrderStateTransition(
                order.status.value, "PAID"
            )

        # Validate payment amount matches order total
        if data.amount != order.total_amount:
            raise DomainError(
                f"Payment amount {data.amount} does not match order total {order.total_amount}"
            )

        # Validate currency matches
        if data.currency != order.currency:
            raise DomainError(
                f"Payment currency {data.currency} does not match order currency {order.currency}"
            )

        # Check no pending/completed payment already exists for this order
        existing = await self._session.execute(
            select(Payment).where(
                Payment.order_id == data.order_id,
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.COMPLETED]),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DomainError("A payment already exists for this order")

        payment = Payment(
            order_id=data.order_id,
            amount=data.amount,
            currency=data.currency,
            method=data.method,
            status=PaymentStatus.PENDING,
        )
        created = await self._payment_repo.add(payment)

        # Publish async notification (deferrable work)
        await publish_message(
            "oms.notifications",
            {
                "type": "payment.initiated",
                "payment_id": created.id,
                "order_id": data.order_id,
            },
        )

        return created

    async def verify_payment(self, data: PaymentVerification) -> Payment:
        """Accountant verifies a payment (back-office, relaxed latency).

        On successful verification (status == COMPLETED), transitions the
        order to PAID. Uses optimistic locking on the order via
        order_version to prevent concurrent modifications.
        """
        payment = await self._payment_repo.get_or_fail(data.payment_id)

        if payment.status != PaymentStatus.PENDING:
            raise PaymentAlreadyProcessed()

        if data.status == PaymentStatus.COMPLETED:
            payment.paid_at = datetime.now(timezone.utc)

            # Transition order to PAID with optimistic locking
            order = await self._order_repo.get_with_items_or_fail(payment.order_id)

            # Optimistic lock check on the order
            if order.version != data.order_version:
                raise OptimisticLockError()

            if order.status != OrderStatus.INVOICED:
                raise InvalidOrderStateTransition(
                    order.status.value, "PAID"
                )
            order.status = OrderStatus.PAID
            order.updated_at = datetime.now(timezone.utc)
            self._session.add(order)
        self._session.add(payment)
        try:
            await self._session.flush()
        except StaleDataError:
            raise OptimisticLockError()

        await publish_message(
            "oms.notifications",
            {
                "type": "payment.verified",
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "status": data.status.value,
            },
        )

        return payment

    async def get_payment(self, payment_id: int) -> Payment:
        return await self._payment_repo.get_or_fail(payment_id)

    async def list_payments_by_order(self, order_id: int) -> list[Payment]:
        result = await self._session.execute(
            select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at)
        )
        return list(result.scalars().all())
