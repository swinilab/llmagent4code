"""Order router exposing order lifecycle endpoints."""
from fastapi import APIRouter, HTTPException

from app.controllers.order_controller import place_order, accept_order, get_order

router = APIRouter()

@router.post('', response_model=None)
async def create_order(dto):
    return await place_order(dto)

@router.post('/{order_id}/accept')
def accept(order_id: str):
    return accept_order(order_id)

@router.get('/{order_id}')
def retrieve(order_id: str):
    return get_order(order_id)
