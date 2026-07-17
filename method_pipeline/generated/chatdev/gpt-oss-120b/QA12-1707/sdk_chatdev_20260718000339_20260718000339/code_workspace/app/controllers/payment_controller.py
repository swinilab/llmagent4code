from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..services.order_service import OrderService
from ..database import get_session
from ..models import Payment
from pydantic import BaseModel

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    method: str

@router.post("/", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, session: Session = Depends(get_session)):
    try:
        payment = OrderService.record_payment(session, payload.order_id, payload.amount, payload.method)
        return payment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
