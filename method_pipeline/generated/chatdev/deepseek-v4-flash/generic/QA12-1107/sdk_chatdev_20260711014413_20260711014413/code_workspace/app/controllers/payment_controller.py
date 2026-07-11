"""
Payment REST controller.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from app.infrastructure.queue_manager import QueueManager
from app.models.enums import PaymentStatus
from app.schemas.payment_schema import (
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
)
from app.services.payment_service import PaymentService


def create_payment_router(
    dep_service: Callable[[], PaymentService],
    queue_mgr: QueueManager | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])

    @router.post("", status_code=202)
    async def process_payment(
        body: PaymentCreate,
        service: PaymentService = Depends(dep_service),
    ):
        """Step 4: Customer pays invoice (queued for async processing)."""
        if queue_mgr is None:
            # Fallback: process synchronously
            try:
                return await service.process_payment(
                    order_id=body.order_id,
                    amount=body.amount,
                    currency=body.currency,
                    method=body.method,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        enqueued = await queue_mgr.enqueue(
            task_type="process_payment",
            payload={
                "order_id": body.order_id,
                "amount": body.amount,
                "currency": body.currency,
                "method": body.method.value if hasattr(body.method, 'value') else body.method,
            },
            essential=True,
        )
        if not enqueued:
            raise HTTPException(status_code=503, detail="System busy, try again later")
        return {"status": "accepted", "message": "Payment queued for processing"}

    @router.get("/{payment_id}", response_model=PaymentResponse)
    async def get_payment(
        payment_id: str,
        service: PaymentService = Depends(dep_service),
    ):
        payment = await service.get_payment(payment_id)
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment

    @router.get("", response_model=PaymentListResponse)
    async def list_payments(
        status: PaymentStatus | None = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        service: PaymentService = Depends(dep_service),
    ):
        payments, total = await service.list_payments(
            status=status, skip=skip, limit=limit
        )
        return PaymentListResponse(payments=payments, total=total)

    @router.put("/{payment_id}/verify", response_model=PaymentResponse)
    async def verify_payment(
        payment_id: str,
        service: PaymentService = Depends(dep_service),
    ):
        """Step 5: Accountant verifies payment."""
        try:
            return await service.verify_payment(payment_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return router
