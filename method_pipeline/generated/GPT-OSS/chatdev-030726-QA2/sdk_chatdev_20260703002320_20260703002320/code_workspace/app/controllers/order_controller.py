"""
Order API endpoints implementing the workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate, OrderOut, OrderUpdate
from app.services.order_service import OrderService
from app.controllers.dependencies import get_db

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: OrderCreate,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    try:
        order = service.place_order(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order

@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    try:
        order = service.update_status(order_id, status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return order

@router.get("/", response_model=list[OrderOut])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.list_orders(skip, limit)
