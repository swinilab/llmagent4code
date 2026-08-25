"""Payment controller."""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import EntityId, get_payment_service
from app.domain.enums import PaymentStatus
from app.domain.models import PaymentCreate, PaymentRead, PaymentVerification
from app.services.services import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])

Service = Annotated[PaymentService, Depends(get_payment_service)]


@router.post(
    "",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Customer pays an invoiced order (workflow step 4)",
    responses={
        400: {"description": "Field constraint violation or amount mismatch"},
        404: {"description": "orderRef not found"},
        409: {"description": "Order not INVOICED, or already paid"},
    },
)
async def create_payment(payload: PaymentCreate, service: Service) -> PaymentRead:
    return await service.create(payload)


@router.get(
    "/{entity_id}",
    response_model=PaymentRead,
    summary="Fetch a payment by id",
    responses={400: {"description": "Malformed id"}, 404: {"description": "Not found"}},
)
async def get_payment(entity_id: EntityId, service: Service) -> PaymentRead:
    return await service.get(entity_id)


@router.patch(
    "/{entity_id}/verification",
    response_model=PaymentRead,
    summary="Accountant verifies or rejects the payment (workflow step 5)",
    responses={
        400: {"description": "Malformed id or unknown status"},
        404: {"description": "Not found"},
        409: {"description": "Illegal payment transition"},
    },
)
async def verify_payment(
    entity_id: EntityId, payload: PaymentVerification, service: Service
) -> PaymentRead:
    return await service.verify(entity_id, payload.status)


@router.post(
    "/{entity_id}/verify",
    response_model=PaymentRead,
    summary="Shorthand for verifying a payment (workflow step 5)",
    responses={404: {"description": "Not found"}, 409: {"description": "Illegal transition"}},
)
async def verify_payment_shorthand(entity_id: EntityId, service: Service) -> PaymentRead:
    return await service.verify(entity_id, PaymentStatus.VERIFIED)
