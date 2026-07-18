"""
Payment controller — REST endpoint handlers for payment operations.

Covers payment creation (step 4) and verification (step 5).
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from oms.schemas.payment import PaymentCreate, PaymentRead, PaymentVerify
from oms.schemas.common import PaginatedResponse
from oms.services.payment import PaymentService, PaymentError


class PaymentController:
    """Handles payment creation and verification endpoints."""

    async def create_payment(self, data: PaymentCreate, session: AsyncSession) -> PaymentRead:
        service = PaymentService(session)
        try:
            payment = await service.create_payment(data)
        except PaymentError as exc:
            # Distinguish circuit-open (503) from validation errors (400)
            if "circuit open" in str(exc).lower():
                raise HTTPException(status_code=503, detail=str(exc))
            raise HTTPException(status_code=400, detail=str(exc))
        return PaymentRead.model_validate(payment)

    async def get_payment(self, payment_id: str, session: AsyncSession) -> PaymentRead:
        service = PaymentService(session)
        payment = await service.get_payment(payment_id)
        if payment is None:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        return PaymentRead.model_validate(payment)

    async def verify_payment(self, payment_id: str, data: PaymentVerify, session: AsyncSession) -> PaymentRead:
        service = PaymentService(session)
        try:
            payment = await service.verify_payment(payment_id, data)
        except PaymentError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if payment is None:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        return PaymentRead.model_validate(payment)

    async def list_payments(self, session: AsyncSession, page: int = 1, page_size: int = 20) -> PaginatedResponse[PaymentRead]:
        service = PaymentService(session)
        items, total = await service.list_payments(page=page, page_size=page_size)
        return PaginatedResponse[PaymentRead].create(
            items=[PaymentRead.model_validate(p) for p in items],
            total=total, page=page, page_size=page_size,
        )

    async def list_order_payments(self, order_id: str, session: AsyncSession) -> list[PaymentRead]:
        service = PaymentService(session)
        payments = await service.list_payments_by_order(order_id)
        return [PaymentRead.model_validate(p) for p in payments]


payment_controller = PaymentController()