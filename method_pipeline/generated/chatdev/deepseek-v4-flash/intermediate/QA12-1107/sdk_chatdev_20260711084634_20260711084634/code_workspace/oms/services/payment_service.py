"""
Payment service: payment processing operations.

Payment verification is an Accountant operation (not on the latency-critical
checkout path). It can be degraded under load (NFR 2.1).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from oms.adapters.repositories import PaymentRepository
from oms.domain.enums import PaymentMethod, PaymentStatus
from oms.domain.models import Money, Payment
from oms.infrastructure.circuit_breaker import get_circuit_breaker
from oms.infrastructure.database import get_session, get_readonly_session

logger = logging.getLogger(__name__)

_payment_repo = PaymentRepository()


class PaymentService:
    """Business logic for payment operations."""

    async def get_payment(self, payment_id: str) -> Payment:
        """Get a payment by ID."""
        async with get_readonly_session() as session:
            return await _payment_repo.get_by_id(session, payment_id)

    async def get_payments_by_order(self, order_id: str) -> list[Payment]:
        """Get all payments for an order (degradable — NFR 2.1)."""
        cb = get_circuit_breaker("payment_history")
        async with get_readonly_session() as session:
            try:
                return await cb.call(
                    _payment_repo.get_by_order, session, order_id
                )
            except Exception:
                logger.warning("Payment history degraded for order %s", order_id)
                return []

    async def record_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str,
        method: str,
        transaction_id: str,
    ) -> Payment:
        """Record a payment (called by payment gateway callback)."""
        async with get_session() as session:
            payment = Payment(
                order_id=order_id,
                amount=Money(amount=amount, currency=currency),
                status=PaymentStatus.COMPLETED,
                method=PaymentMethod(method),
                transaction_id=transaction_id,
            )
            await _payment_repo.save(session, payment)
            logger.info("Payment %s recorded for order %s", payment.id, order_id)
            return payment
