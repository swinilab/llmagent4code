"""
Routers for Order endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import OrderService, OrderStateError

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    return OrderService.create(db, data)


@router.get("", response_model=list[OrderResponse])
def list_orders(
    customer_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if customer_id:
        return OrderService.list_by_customer(db, customer_id, skip=skip, limit=limit)
    return OrderService.list_all(db, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = OrderService.get_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: str, data: OrderStatusUpdate, db: Session = Depends(get_db)):
    try:
        order = OrderService.update_status(db, order_id, data)
    except OrderStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: str, db: Session = Depends(get_db)):
    if not OrderService.delete(db, order_id):
        raise HTTPException(status_code=404, detail="Order not found")
