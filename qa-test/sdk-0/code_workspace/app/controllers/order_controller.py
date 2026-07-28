from fastapi import APIRouter, HTTPException
import uuid

from app.models import OrderCreateDTO, OrderDTO, OrderStatus
from app.services.order_service import OrderService

router = APIRouter()

@router.post('', response_model=OrderDTO)
async def place_order(dto: OrderCreateDTO):
    return await OrderService.place_order(dto)

@router.post('/{order_id}/accept')
def accept_order(order_id: str):
    return OrderService.accept_order(order_id)

@router.get('/{order_id}', response_model=OrderDTO)
@router.get('/{order_id}', response_model=OrderDTO)
def get_order(order_id: str):
    from app.repositories import OrderRepository
    order = OrderRepository.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    return order
    if not ord:
        raise HTTPException(status_code=404, detail='Order not found')
    return ord
