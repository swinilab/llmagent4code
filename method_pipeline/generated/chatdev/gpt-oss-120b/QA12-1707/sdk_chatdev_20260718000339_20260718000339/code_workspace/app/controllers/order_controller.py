"""FastAPI controller for Order workflow endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..services.order_service import OrderService
from ..database import get_session
from ..models import Order, OrderStatus, Invoice, Payment
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderItemDTO(BaseModel):
    product_id: int
    quantity: int

class OrderCreateDTO(BaseModel):
    customer_id: int
    items: List[OrderItemDTO]

class InvoiceCreateDTO(BaseModel):
    billing_info: str

class PaymentCreateDTO(BaseModel):
    amount: float
    method: str

@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreateDTO, session: Session = Depends(get_session)):
    try:
        return OrderService.create_order(
            session,
            customer_id=payload.customer_id,
            items=[item.dict() for item in payload.items],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{order_id}/accept", response_model=Order)
def accept_order(order_id: int, session: Session = Depends(get_session)):
    try:
        return OrderService.accept_order(session, order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{order_id}/invoice", response_model=Invoice)
def create_invoice(order_id: int, payload: InvoiceCreateDTO, session: Session = Depends(get_session)):
    try:
        return OrderService.create_invoice(session, order_id, payload.billing_info)
    except HTTPException as he:
        # Propagate feature‑toggle 503 errors unchanged
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{order_id}/pay", response_model=Payment)
def pay_order(order_id: int, payload: PaymentCreateDTO, session: Session = Depends(get_session)):
    try:
        return OrderService.record_payment(session, order_id, payload.amount, payload.method)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{order_id}/ship", response_model=Order)
def ship_order(order_id: int, session: Session = Depends(get_session)):
    try:
        return OrderService.ship_order(session, order_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{order_id}/close", response_model=Order)
def close_order(order_id: int, session: Session = Depends(get_session)):
    try:
        return OrderService.close_order(session, order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{order_id}", response_model=Order)
def get_order(order_id: int, session: Session = Depends(get_session)):
    order = OrderService.get_order(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order