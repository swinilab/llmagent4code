from fastapi import APIRouter, HTTPException
import uuid

from app.models import PaymentCreateDTO, PaymentDTO
from app.services.payment_service import PaymentService

router = APIRouter()

@router.post('', response_model=PaymentDTO)
def create_payment(dto: PaymentCreateDTO):
    return PaymentService.create_payment(dto)

@router.post('/{payment_id}/verify')
def verify_payment(payment_id: str):
    return PaymentService.verify_payment(payment_id)
