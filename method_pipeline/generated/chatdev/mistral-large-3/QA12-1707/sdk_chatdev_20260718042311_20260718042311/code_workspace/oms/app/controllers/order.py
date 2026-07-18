"""
Order REST controller.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.order import OrderService
from app.models.order import OrderStatus
from app.schemas.order import OrderCreate, OrderRead
from app.db.session import get_db

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order."""
    service = OrderService(db)
    return service.create_order(order)


@router.get("/{order_id}", response_model=OrderRead)
def read_order(order_id: int, db: Session = Depends(get_db)):
    """Get order by ID."""
    service = OrderService(db)
    return service.get_order(order_id)


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(order_id: int, status: OrderStatus, db: Session = Depends(get_db)):
    """Update order status."""
    service = OrderService(db)
    return service.update_order_status(order_id, status)


@router.get("", response_model=list[OrderRead])
def read_orders(db: Session = Depends(get_db)):
    """List all orders."""
    service = OrderService(db)
"""
@router.patch("/{order_id}/accept", response_model=OrderRead)
def accept_order(order_id: int, db: Session = Depends(get_db)):
    """Accept an order (Order Staff)."""
    service = OrderService(db)
    return service.accept_order(order_id)


@router.patch("/{order_id}/ship", response_model=OrderRead)
def ship_order(order_id: int, db: Session = Depends(get_db)):
    """Ship an order (Order Staff)."""
    service = OrderService(db)
    return service.ship_order(order_id)


@router.patch("/{order_id}/close", response_model=OrderRead)
def close_order(order_id: int, db: Session = Depends(get_db)):
    """Close an order (Order Staff)."""
    service = OrderService(db)
    return service.close_order(order_id)


@router.get("/{order_id}", response_model=OrderRead)
def read_order(order_id: int, db: Session = Depends(get_db)):
    """Get order by ID."""
    service = OrderService(db)
    return service.get_order(order_id)


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(order_id: int, status: OrderStatus, db: Session = Depends(get_db)):
    """Update order status."""
    service = OrderService(db)
    return service.update_order_status(order_id, status)


@router.get("", response_model=list[OrderRead])
def read_orders(db: Session = Depends(get_db)):
    """List all orders."""
    service = OrderService(db)
    return service.list_orders()