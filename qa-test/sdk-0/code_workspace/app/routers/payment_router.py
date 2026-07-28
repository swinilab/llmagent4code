"""
Payment router for processing payments.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.schemas import PaymentCreateDTO
from app.services.payment_service import process_payment_async

router = APIRouter()

@router.post("/payment", status_code=status.HTTP_201_CREATED)
async def pay(payload: PaymentCreateDTO):
    try:
        payment = await process_payment_async(
            order_id=payload.orderRef,
            amount=str(payload.amount),
            method=payload.method,
        )
        return {"paymentId": payment.id, "status": payment.status}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
