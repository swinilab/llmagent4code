from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services import order_service
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate
from app.db.models import OrderStatus

router = APIRouter()

@router.get("/", response_model=List[OrderResponse])
async def read_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    orders = await order_service.get_orders(db, skip=skip, limit=limit)
    return orders

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.create_order_with_items(db, order_in)

@router.get("/{order_id}", response_model=OrderResponse)
async def read_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_in: OrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.update_order_status(db, order_id, order_in.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    success = await order_service.delete_order(db, order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return None

@router.post("/{order_id}/process-workflow", response_model=dict)
async def process_order_workflow(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await order_service.process_order_workflow(db, order_id)
    return result