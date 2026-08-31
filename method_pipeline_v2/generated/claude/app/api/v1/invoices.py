"""Invoice controller."""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import EntityId, get_invoice_service
from app.domain.models import InvoiceCreate, InvoiceRead
from app.services.services import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])

Service = Annotated[InvoiceService, Depends(get_invoice_service)]


@router.post(
    "",
    response_model=InvoiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Accountant issues an invoice for an ACCEPTED order (workflow step 3)",
    responses={
        400: {"description": "Field constraint violation"},
        404: {"description": "orderRef not found"},
        409: {"description": "Order not ACCEPTED, or already invoiced"},
    },
)
async def create_invoice(payload: InvoiceCreate, service: Service) -> InvoiceRead:
    return await service.create(payload)


@router.get(
    "/{entity_id}",
    response_model=InvoiceRead,
    summary="Fetch an invoice by id",
    responses={400: {"description": "Malformed id"}, 404: {"description": "Not found"}},
)
async def get_invoice(entity_id: EntityId, service: Service) -> InvoiceRead:
    return await service.get(entity_id)
