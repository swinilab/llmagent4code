from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, crud
from app.database import get_db

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: schemas.InvoiceCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new invoice.
    """
    # Check if order exists
    order = await crud.get_order(db, order_id=invoice_in.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # Check if invoice number already exists
    existing_invoice = await crud.get_invoice_by_number(db, invoice_number=invoice_in.invoice_number)
    if existing_invoice:
        raise HTTPException(status_code=400, detail="Invoice number already exists")
    return await crud.create_invoice(db, invoice_in=invoice_in)


@router.get("/", response_model=List[schemas.Invoice])
async def read_invoices(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve invoices.
    """
    invoices = await crud.get_invoices(db, skip=skip, limit=limit)
    return invoices


@router.get("/{invoice_id}", response_model=schemas.Invoice)
async def read_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific invoice by ID.
    """
    invoice = await crud.get_invoice(db, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.put("/{invoice_id}", response_model=schemas.Invoice)
async def update_invoice(
    invoice_id: int,
    invoice_in: schemas.InvoiceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an invoice.
    """
    invoice = await crud.update_invoice(db, invoice_id=invoice_id, invoice_in=invoice_in)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.delete("/{invoice_id}", response_model=schemas.Invoice)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an invoice.
    """
    invoice = await crud.delete_invoice(db, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice