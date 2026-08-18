"""
Invoice controller with REST endpoints
Implements NFR 2.1 Exception Detection via validation and error handling
Implements NFR 2.4 Transactions via service layer
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from oms.infrastructure.database import get_async_session
from oms.service.invoice_service import InvoiceService
from oms.domain.models import Invoice, InvoiceCreate, InvoiceStatus
from oms.infrastructure.exceptions import NotFoundException, ConflictException
from oms.infrastructure.event.rate_limiter import RateLimiter

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

def get_invoice_service(session: AsyncSession = Depends(get_async_session)) -> InvoiceService:
    """Get invoice service instance"""
    return InvoiceService(session)

@router.get("", response_model=List[Invoice])
async def list_invoices(
    service: InvoiceService = Depends(get_invoice_service)
):
    """List all invoices"""
    return await service.get_all()

@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service)
):
    """Get invoice by ID"""
    return await service.get_by_id(invoice_id)

@router.get("/order/{order_id}", response_model=Invoice)
async def get_invoice_by_order(
    order_id: str,
    service: InvoiceService = Depends(get_invoice_service)
):
    """Get invoice by order ID"""
    return await service.get_by_order(order_id)

@router.post("", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Create new invoice (Accountant)
    NFR 1.1: Rate limited
    NFR 2.4: Transactional
    """
    # Check rate limit (NFR 1.1)
    rate_limiter = RateLimiter.get_instance()
    if not await rate_limiter.is_allowed("invoice_create"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return await service.create(invoice)

@router.put("/{invoice_id}/status", response_model=Invoice)
async def update_invoice_status(
    invoice_id: str,
    new_status: InvoiceStatus,
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Update invoice status (Accountant)
    NFR 2.4: Transactional state update
    """
    return await service.update_status(invoice_id, new_status)

@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service)
):
    """Delete invoice"""
    success = await service.delete(invoice_id)
    if not success:
        raise NotFoundException(f"Invoice {invoice_id} not found")

invoice_router = router
