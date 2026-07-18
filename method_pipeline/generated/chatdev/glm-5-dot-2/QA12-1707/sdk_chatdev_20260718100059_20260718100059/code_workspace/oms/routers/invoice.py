"""
Invoice routes — /api/v1/invoices

POST   /              Create invoice (step 3: accountant creates invoice)
GET    /              List invoices (paginated)
GET    /{id}          Get invoice
GET    /order/{id}    Get invoice by order ID
PUT    /{id}/status   Update invoice status
POST   /overdue       Mark overdue invoices (admin/cron)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from oms.controllers.invoice import invoice_controller
from oms.database import get_session
from oms.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceStatusUpdate
from oms.schemas.common import PaginatedResponse

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=InvoiceRead, status_code=201)
async def create_invoice(data: InvoiceCreate, session: AsyncSession = Depends(get_session)) -> InvoiceRead:
    """Create an invoice for an accepted order (step 3: accountant creates invoice)."""
    return await invoice_controller.create_invoice(data, session)


@router.get("/", response_model=PaginatedResponse[InvoiceRead])
async def list_invoices(page: int = 1, page_size: int = 20, session: AsyncSession = Depends(get_session)) -> PaginatedResponse[InvoiceRead]:
    """List all invoices with pagination."""
    return await invoice_controller.list_invoices(session, page=page, page_size=page_size)


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)) -> InvoiceRead:
    """Get an invoice by ID."""
    return await invoice_controller.get_invoice(invoice_id, session)


@router.get("/order/{order_id}", response_model=InvoiceRead)
async def get_invoice_by_order(order_id: str, session: AsyncSession = Depends(get_session)) -> InvoiceRead:
    """Get the invoice for a specific order."""
    return await invoice_controller.get_invoice_by_order(order_id, session)


@router.put("/{invoice_id}/status", response_model=InvoiceRead)
async def update_invoice_status(invoice_id: str, data: InvoiceStatusUpdate, session: AsyncSession = Depends(get_session)) -> InvoiceRead:
    """Update an invoice's status."""
    return await invoice_controller.update_invoice_status(invoice_id, data, session)


@router.post("/overdue")
async def mark_overdue(session: AsyncSession = Depends(get_session)) -> dict:
    """Mark all issued invoices past their due date as OVERDUE."""
    return await invoice_controller.mark_overdue(session)