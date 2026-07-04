"""
Routers for the order lifecycle workflow.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payment import PaymentMethod
from app.schemas.order import OrderResponse
from app.schemas.payment import PaymentResponse
from app.schemas.invoice import InvoiceResponse
from app.services.workflow_service import WorkflowService, WorkflowError
from app.services.order_service import OrderStateError
from app.services.payment_service import PaymentStateError
from app.services.invoice_service import InvoiceStateError

router = APIRouter(prefix="/api/v1/workflow", tags=["Workflow"])


@router.post("/orders/{order_id}/accept", response_model=OrderResponse)
def accept_order(order_id: str, db: Session = Depends(get_db)):
    """Step 2: Order Staff reviews & accepts an order."""
    try:
        return WorkflowService.accept_order(db, order_id)
    except (WorkflowError, OrderStateError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/orders/{order_id}/invoice", response_model=InvoiceResponse)
def create_invoice_for_order(
    order_id: str,
    billing_info: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Step 3: Accountant creates invoice for accepted order."""
    try:
        return WorkflowService.create_invoice_for_order(db, order_id, billing_info)
    except (WorkflowError, OrderStateError, InvoiceStateError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/invoices/{invoice_id}/pay", response_model=PaymentResponse)
def pay_invoice(
    invoice_id: str,
    payment_method: PaymentMethod = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Step 4: Customer pays invoice."""
    try:
        return WorkflowService.pay_invoice(db, invoice_id, payment_method)
    except (WorkflowError, OrderStateError, PaymentStateError, InvoiceStateError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/payments/{payment_id}/verify", response_model=PaymentResponse)
def verify_payment(payment_id: str, db: Session = Depends(get_db)):
    """Step 5: Accountant verifies payment."""
    try:
        return WorkflowService.verify_payment(db, payment_id)
    except (WorkflowError, OrderStateError, PaymentStateError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/orders/{order_id}/ship", response_model=OrderResponse)
def ship_order(order_id: str, db: Session = Depends(get_db)):
    """Step 6: Order Staff ships paid order."""
    try:
        return WorkflowService.ship_order(db, order_id)
    except (WorkflowError, OrderStateError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/orders/{order_id}/close", response_model=OrderResponse)
def close_order(order_id: str, db: Session = Depends(get_db)):
    """Step 7: Order Staff closes completed order."""
    try:
        return WorkflowService.close_order(db, order_id)
    except (WorkflowError, OrderStateError) as e:
        raise HTTPException(status_code=409, detail=str(e))
