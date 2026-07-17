from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..services.order_service import OrderService
from ..database import get_session
from ..models import Invoice
from pydantic import BaseModel

router = APIRouter(prefix="/invoices", tags=["invoices"])

class InvoiceCreate(BaseModel):
    order_id: int
    billing_info: str
    due_in_days: int = 30

@router.post("/", response_model=Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, session: Session = Depends(get_session)):
    try:
        # OrderService.create_invoice will handle due date using due_in_days if provided
        invoice = OrderService.create_invoice(session, payload.order_id, payload.billing_info, payload.due_in_days)
        return invoice
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
