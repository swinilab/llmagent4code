"""
REST controller for Order entity.
Provides CRUD + status transition endpoints under /api/v1/orders.
All workflow steps delegate to OrderWorkflow for orchestration consistency.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.enums import OrderStatus
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate
from app.services.order_service import OrderService
from app.workflows.order_workflow import OrderWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Place a new order (Customer step 1). Delegates to OrderWorkflow."""
    try:
        order = await OrderWorkflow.place_order(db, data)
    except Exception as e:
        logger.exception("Order creation failed")
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")
    return order


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve an order by ID."""
    try:
        order = await OrderService.get_by_id(db, order_id)
    except Exception as e:
        logger.exception("Failed to retrieve order %s", order_id)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve order: {str(e)}")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/", response_model=List[OrderRead])
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[OrderStatus] = Query(None),
    customer_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List orders with optional filters and pagination."""
    try:
        orders = await OrderService.get_all(db, skip=skip, limit=limit, status=status, customer_id=customer_id)
    except Exception as e:
        logger.exception("Failed to list orders")
        raise HTTPException(status_code=500, detail=f"Failed to list orders: {str(e)}")
    return orders


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(order_id: str, data: OrderUpdate, db: AsyncSession = Depends(get_db)):
    """Update order fields or transition status."""
    try:
        order = await OrderService.update(db, order_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Failed to update order %s", order_id)
        raise HTTPException(status_code=500, detail=f"Failed to update order: {str(e)}")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/review", response_model=OrderRead)
async def review_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Order Staff reviews an order (step 2a). Delegates to OrderWorkflow."""
    try:
        order = await OrderWorkflow.review_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Failed to review order %s", order_id)
        raise HTTPException(status_code=500, detail=f"Failed to review order: {str(e)}")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/accept", response_model=OrderRead)
async def accept_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Order Staff accepts a reviewed order (step 2b). Delegates to OrderWorkflow."""
    try:
        order = await OrderWorkflow.accept_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Failed to accept order %s", order_id)
        raise HTTPException(status_code=500, detail=f"Failed to accept order: {str(e)}")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/ship", response_model=OrderRead)
async def ship_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Order Staff ships a paid order (step 6). Delegates to OrderWorkflow."""
    try:
        order = await OrderWorkflow.ship_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Failed to ship order %s", order_id)
        raise HTTPException(status_code=500, detail=f"Failed to ship order: {str(e)}")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/close", response_model=OrderRead)
async def close_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Order Staff closes a completed order (step 7). Delegates to OrderWorkflow."""
    try:
        order = await OrderWorkflow.close_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Failed to close order %s", order_id)
        raise HTTPException(status_code=500, detail=f"Failed to close order: {str(e)}")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an order by ID."""
    try:
        deleted = await OrderService.delete(db, order_id)
    except Exception as e:
        logger.exception("Failed to delete order %s", order_id)
        raise HTTPException(status_code=500, detail=f"Failed to delete order: {str(e)}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Order not found")
