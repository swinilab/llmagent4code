from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from schemas import OrderCreate, OrderRead
from services import OrderService
from database import get_db
from config import get_settings

settings = get_settings()
router = APIRouter(prefix=f"/api/{settings.API_VERSION}/orders", tags=["orders"])

@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.place_order(payload.customer_id, [li.dict() for li in payload.line_items])
        return order
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{order_id}/review", response_model=OrderRead)
def review_order(order_id: int, accept: bool, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.review_order(order_id, accept)
        return order
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/{order_id}/invoice", response_model=OrderRead)
def create_invoice(order_id: int, billing_info: str, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        invoice = service.create_invoice(order_id, billing_info)
        return invoice.order
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/{order_id}/pay", response_model=OrderRead)
def pay_order(order_id: int, method: str, amount: float, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        payment = service.record_payment(order_id, method, amount)
        return payment.order
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/{order_id}/ship", response_model=OrderRead)
def ship_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.ship_order(order_id)
        return order
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/{order_id}/close", response_model=OrderRead)
def close_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.close_order(order_id)
        return order
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))