"""Payment business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.payment import Payment, PaymentMethod, PaymentStatus
from src.repositories.payment import PaymentRepository
from src.schemas.payment import PaymentCreate
from src.utils.exceptions import NotFoundError, ValidationError


class PaymentService:
    """Orchestrates payment processing."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = PaymentRepository(session)

    async def create(self, payload: PaymentCreate) -> Payment:
        """Record a new payment attempt."""
        try:
            method = PaymentMethod(payload.method)
        except ValueError:
            raise ValidationError(f"Invalid payment method: {payload.method}") from None

        payment = Payment(
            order_id=payload.order_id,
            amount=payload.amount,
            method=method,
            status=PaymentStatus.PENDING,
        )
        return await self.repo.add(payment)

    async def get(self, payment_id: str) -> Payment:
        """Retrieve a payment by ID."""
        payment = await self.repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError(f"Payment {payment_id} not found")
        return payment

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Payment]:
        """List all payments."""
        return await self.repo.list_all(limit=limit, offset=offset)

    async def list_by_order(self, order_id: str) -> list[Payment]:
        """List payments for an order."""
        return await self.repo.list_by_order(order_id)

    async def verify(self, payment_id: str, new_status: str) -> Payment:
        """Verify (complete or fail) a payment."""
        payment = await self.get(payment_id)
        try:
            target = PaymentStatus(new_status)
        except ValueError:
            raise ValidationError(f"Invalid payment status: {new_status}") from None

        if target not in (PaymentStatus.COMPLETED, PaymentStatus.FAILED):
            raise ValidationError("Verification must set status to completed or failed")
        payment.status = target
        await self.repo.session.flush()
        return payment
