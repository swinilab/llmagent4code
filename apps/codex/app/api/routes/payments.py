from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_payment_controller
from app.controllers.common import missing_identifier
from app.controllers.payment_controller import PaymentController
from app.domain.schemas import PaymentCreate, PaymentResponse, PaymentWorkflowResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    controller: Annotated[PaymentController, Depends(get_payment_controller)],
) -> PaymentResponse:
    return await controller.create(body)


@router.get("", include_in_schema=False)
async def get_payment_without_id() -> None:
    missing_identifier()


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    controller: Annotated[PaymentController, Depends(get_payment_controller)],
) -> PaymentResponse:
    return await controller.get(payment_id)


@router.post("/{payment_id}/verify", response_model=PaymentWorkflowResponse)
async def verify_payment(
    payment_id: str,
    controller: Annotated[PaymentController, Depends(get_payment_controller)],
) -> PaymentWorkflowResponse:
    return await controller.verify(payment_id)


@router.post("/{payment_id}/reject", response_model=PaymentWorkflowResponse)
async def reject_payment(
    payment_id: str,
    controller: Annotated[PaymentController, Depends(get_payment_controller)],
) -> PaymentWorkflowResponse:
    return await controller.reject(payment_id)
