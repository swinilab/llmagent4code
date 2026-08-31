"""Order controller - creation plus the staff-driven workflow transitions."""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import EntityId, get_order_service
from app.domain.enums import OrderStatus
from app.domain.models import OrderCreate, OrderRead, OrderStatusUpdate
from app.services.services import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

Service = Annotated[OrderService, Depends(get_order_service)]


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order (workflow step 1)",
    responses={
        400: {"description": "Field constraint violation"},
        404: {"description": "customerRef or productRef not found"},
        429: {"description": "Rate limited"},
    },
)
async def create_order(payload: OrderCreate, service: Service) -> OrderRead:
    return await service.create(payload)


@router.get(
    "/{entity_id}",
    response_model=OrderRead,
    summary="Fetch an order by id",
    responses={400: {"description": "Malformed id"}, 404: {"description": "Not found"}},
)
async def get_order(entity_id: EntityId, service: Service) -> OrderRead:
    return await service.get(entity_id)


@router.patch(
    "/{entity_id}/status",
    response_model=OrderRead,
    summary="Drive the order state machine (steps 2, 6, 7)",
    responses={
        400: {"description": "Malformed id or unknown status"},
        404: {"description": "Not found"},
        409: {"description": "Illegal state transition"},
    },
)
async def update_order_status(
    entity_id: EntityId, payload: OrderStatusUpdate, service: Service
) -> OrderRead:
    return await service.transition(entity_id, payload.status)


@router.post(
    "/{entity_id}/accept",
    response_model=OrderRead,
    summary="Order Staff accepts the order (workflow step 2)",
    responses={404: {"description": "Not found"}, 409: {"description": "Illegal transition"}},
)
async def accept_order(entity_id: EntityId, service: Service) -> OrderRead:
    return await service.transition(entity_id, OrderStatus.ACCEPTED)


@router.post(
    "/{entity_id}/ship",
    response_model=OrderRead,
    summary="Order Staff ships the verified order (workflow step 6)",
    responses={404: {"description": "Not found"}, 409: {"description": "Illegal transition"}},
)
async def ship_order(entity_id: EntityId, service: Service) -> OrderRead:
    return await service.transition(entity_id, OrderStatus.SHIPPED)


@router.post(
    "/{entity_id}/close",
    response_model=OrderRead,
    summary="Order Staff closes the completed order (workflow step 7)",
    responses={404: {"description": "Not found"}, 409: {"description": "Illegal transition"}},
)
async def close_order(entity_id: EntityId, service: Service) -> OrderRead:
    return await service.transition(entity_id, OrderStatus.CLOSED)


@router.post(
    "/{entity_id}/cancel",
    response_model=OrderRead,
    summary="Cancel an order that has not shipped",
    responses={404: {"description": "Not found"}, 409: {"description": "Illegal transition"}},
)
async def cancel_order(entity_id: EntityId, service: Service) -> OrderRead:
    return await service.transition(entity_id, OrderStatus.CANCELLED)
