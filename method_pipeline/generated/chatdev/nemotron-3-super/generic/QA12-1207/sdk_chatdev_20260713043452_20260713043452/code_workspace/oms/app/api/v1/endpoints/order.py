from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.services.order import OrderService
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate, OrderUpdate, OrderInDB
from app.schemas.order_item import OrderItemCreate
from app.database import get_db

router = APIRouter()

def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    repo = OrderRepository(db)
    return OrderService(repo)

@router.post("/", response_model=OrderInDB, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    service: OrderService = Depends(get_order_service)
):
    return service.create(order_in)

@router.get("/{order_id}", response_model=OrderInDB)
async def read_order(
    order_id: int,
    service: OrderService = Depends(get_order_service)
):
    order = service.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.get("/", response_model=List[OrderInDB])
async def read_orders(
    skip: int = 0,
    limit: int = 100,
    service: OrderService = Depends(get_order_service)
):
    return service.get_multi(skip=skip, limit=limit)

@router.put("/{order_id}", response_model=OrderInDB)
async def update_order(
    order_id: int,
    order_in: OrderUpdate,
    service: OrderService = Depends(get_order_service)
):
    order = service.update(order_id, order_in)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.delete("/{order_id}", response_model=OrderInDB)
async def delete_order(
    order_id: int,
    service: OrderService = Depends(get_order_service)
):
    order = service.delete(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/{order_id}/items", response_model=dict)
async def add_order_item(
    order_id: int,
    item_in: OrderItemCreate,
    service: OrderService = Depends(get_order_service)
):
    item = service.add_item(order_id, item_in)
    return {"message": "Item added", "item_id": item.id}