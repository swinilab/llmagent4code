"""Order router – handles the full order lifecycle.

All state transitions enforce the state‑machine defined in the domain model.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.api.v1.dtos.order_dto import OrderCreateDTO, OrderResponseDTO
from app.services.order_service import OrderService

router = APIRouter()

order_service = OrderService()

@router.post("/orders", response_model=OrderResponseDTO, tags=["order"])
async def place_order(order: OrderCreateDTO, role: str = Depends()):
    if role != "CUSTOMER":
        raise HTTPException(status_code=403, detail="Only customers can place orders")
    return await order_service.create_order(order)

@router.post("/orders/{order_id}/accept", response_model=OrderResponseDTO, tags=["order"])
async def accept_order(order_id: str, role: str = Depends()):
    if role != "ORDER_STAFF":
        raise HTTPException(status_code=403, detail="Only order staff can accept orders")
    return await order_service.accept_order(order_id)

@router.post("/orders/{order_id}/ship", response_model=OrderResponseDTO, tags=["order"])
async def ship_order(order_id: str, role: str = Depends()):
    if role != "ORDER_STAFF":
        raise HTTPException(status_code=403, detail="Only order staff can ship orders")
    return await order_service.ship_order(order_id)

@router.post("/orders/{order_id}/close", response_model=OrderResponseDTO, tags=["order"])
async def close_order(order_id: str, role: str = Depends()):
    if role != "ORDER_STAFF":
        raise HTTPException(status_code=403, detail="Only order staff can close orders")
    return await order_service.close_order(order_id)

@router.post("/orders/{order_id}/invoice", response_model=OrderResponseDTO, tags=["order"])
async def create_invoice(order_id: str, role: str = Depends()):
    if role != "ACCOUNTANT":
        raise HTTPException(status_code=403, detail="Only accountants can create invoices")
    return await order_service.create_invoice(order_id)

@router.post("/orders/{order_id}/pay", response_model=OrderResponseDTO, tags=["order"])
async def pay_order(order_id: str, role: str = Depends()):
    if role != "CUSTOMER":
        raise HTTPException(status_code=403, detail="Only customers can pay orders")
    return await order_service.pay_order(order_id)
