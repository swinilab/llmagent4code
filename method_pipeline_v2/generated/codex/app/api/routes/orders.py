from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_order_controller
from app.controllers.common import missing_identifier
from app.controllers.order_controller import OrderController
from app.domain.schemas import OrderCreate, OrderResponse, OrderWorkflowResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    controller: Annotated[OrderController, Depends(get_order_controller)],
) -> OrderResponse:
    return await controller.create(body)


@router.get("", include_in_schema=False)
async def get_order_without_id() -> None:
    missing_identifier()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    controller: Annotated[OrderController, Depends(get_order_controller)],
) -> OrderResponse:
    return await controller.get(order_id)


@router.post("/{order_id}/accept", response_model=OrderWorkflowResponse)
async def accept_order(
    order_id: str,
    controller: Annotated[OrderController, Depends(get_order_controller)],
) -> OrderWorkflowResponse:
    return await controller.accept(order_id)


@router.post("/{order_id}/ship", response_model=OrderWorkflowResponse)
async def ship_order(
    order_id: str,
    controller: Annotated[OrderController, Depends(get_order_controller)],
) -> OrderWorkflowResponse:
    return await controller.ship(order_id)


@router.post("/{order_id}/close", response_model=OrderWorkflowResponse)
async def close_order(
    order_id: str,
    controller: Annotated[OrderController, Depends(get_order_controller)],
) -> OrderWorkflowResponse:
    return await controller.close(order_id)


@router.post("/{order_id}/cancel", response_model=OrderWorkflowResponse)
async def cancel_order(
    order_id: str,
    controller: Annotated[OrderController, Depends(get_order_controller)],
) -> OrderWorkflowResponse:
    return await controller.cancel(order_id)

