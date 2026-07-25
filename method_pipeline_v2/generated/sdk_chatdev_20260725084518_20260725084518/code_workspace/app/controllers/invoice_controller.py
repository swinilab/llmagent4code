"""
Invoice controller with REST endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
from app.db.connection_pool import get_db
from app.services.invoice_service import InvoiceService, InvoiceValidationError, InvoiceTransitionError
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


class InvoiceCreateRequest(BaseModel):
    """Request model for creating an invoice"""
    orderRef: str
    issueDate: Optional[str] = None
    dueDate: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Response model for invoice"""
    id: str
    orderRef: str
    billingInfo: dict
    totalAmount: str
    issueDate: str
    dueDate: str
    status: str


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(request: InvoiceCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new invoice for an accepted order"""
    service = InvoiceService(session)
    try:
        invoice = await service.create_invoice(
            order_ref=request.orderRef,
            issue_date=request.issueDate,
            due_date=request.dueDate,
        )
        return InvoiceResponse(
            id=str(invoice.id),
            orderRef=str(invoice.orderRef),
            billingInfo=invoice.billingInfo.model_dump(),
            totalAmount=str(invoice.totalAmount),
            issueDate=invoice.issueDate,
            dueDate=invoice.dueDate,
            status=invoice.status,
        )
    except InvoiceValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvoiceTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_db)):
    """List all invoices"""
    service = InvoiceService(session)
    invoices = await service.get_all_invoices(limit, offset)
    return [
        InvoiceResponse(
            id=str(i.id),
            orderRef=str(i.orderRef),
            billingInfo=i.billingInfo.model_dump(),
            totalAmount=str(i.totalAmount),
            issueDate=i.issueDate,
            dueDate=i.dueDate,
            status=i.status,
        )
        for i in invoices
    ]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, session: AsyncSession = Depends(get_db)):
    """Get invoice by ID"""
    service = InvoiceService(session)
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return InvoiceResponse(
        id=str(invoice.id),
        orderRef=str(invoice.orderRef),
        billingInfo=invoice.billingInfo.model_dump(),
        totalAmount=str(invoice.totalAmount),
        issueDate=invoice.issueDate,
        dueDate=invoice.dueDate,
        status=invoice.status,
    )


@router.get("/order/{order_ref}", response_model=InvoiceResponse)
async def get_invoice_by_order(order_ref: str, session: AsyncSession = Depends(get_db)):
    """Get invoice by order reference"""
    service = InvoiceService(session)
    invoice = await service.get_invoice_by_order(order_ref)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found for order")
    
    return InvoiceResponse(
        id=str(invoice.id),
        orderRef=str(invoice.orderRef),
        billingInfo=invoice.billingInfo.model_dump(),
        totalAmount=str(invoice.totalAmount),
        issueDate=invoice.issueDate,
        dueDate=invoice.dueDate,
        status=invoice.status,
    )


@router.put("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(invoice_id: str, session: AsyncSession = Depends(get_db)):
    """Cancel invoice"""
    service = InvoiceService(session)
    try:
        invoice = await service.cancel_invoice(invoice_id)
        return InvoiceResponse(
            id=str(invoice.id),
            orderRef=str(invoice.orderRef),
            billingInfo=invoice.billingInfo.model_dump(),
            totalAmount=str(invoice.totalAmount),
            issueDate=invoice.issueDate,
            dueDate=invoice.dueDate,
            status=invoice.status,
        )
    except InvoiceValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvoiceTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
