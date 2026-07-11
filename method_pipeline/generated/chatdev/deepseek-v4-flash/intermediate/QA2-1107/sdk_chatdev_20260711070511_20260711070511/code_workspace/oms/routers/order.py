"""
Order REST router – full lifecycle management.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from oms.database import get_db
from oms.models.enums import OrderStatus
from oms.schemas.order import OrderCreate, OrderResponse, OrderUpdateStatus
from oms.services.order_service import ConcurrentModificationError, OrderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.create_order(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(order)
    # Load line items
    order.line_items = service.repo.get_line_items(order.id)
    return order


@router.get("", response_model=List[OrderResponse])
def list_orders(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List orders with optional filtering by status and/or customer_id.
    When both filters are provided, they are combined (AND logic).
    """
    service = OrderService(db)

    # Parse status filter if provided
    status_filter = None
    if status is not None:
        try:
            status_filter = OrderStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Apply filters: combine status and customer_id when both are given
    if status_filter is not None and customer_id is not None:
        # Filter by both – fetch by customer, then filter by status in Python
        all_customer_orders = service.list_by_customer(customer_id)
        orders = [o for o in all_customer_orders if o.status == status_filter]
    elif status_filter is not None:
        orders = service.list_by_status(status_filter)
    elif customer_id is not None:
        orders = service.list_by_customer(customer_id)
    else:
        orders = service.list_orders(skip, limit)

    # Eager-load line items
    for o in orders:
        o.line_items = service.repo.get_line_items(o.id)
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    service = OrderService(db)
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.line_items = service.repo.get_line_items(order.id)
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: str, data: OrderUpdateStatus, db: Session = Depends(get_db)
):
    service = OrderService(db)
    try:
        order = service.transition_status(order_id, data.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConcurrentModificationError as e:
        raise HTTPException(status_code=409, detail=str(e))
    order.line_items = service.repo.get_line_items(order.id)
    return order
