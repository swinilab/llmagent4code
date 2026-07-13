from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import invoice as crud_invoice
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse

async def get_invoice(db: AsyncSession, invoice_id: int) -> Optional[InvoiceResponse]:
    obj = await crud_invoice.get_invoice(db, invoice_id)
    return InvoiceResponse.from_orm(obj) if obj else None

async def get_invoice_by_order(db: AsyncSession, order_id: int) -> Optional[InvoiceResponse]:
    obj = await crud_invoice.get_invoice_by_order(db, order_id)
    return InvoiceResponse.from_orm(obj) if obj else None

async def get_invoices(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[InvoiceResponse]:
    objs = await crud_invoice.get_invoices(db, skip, limit)
    return [InvoiceResponse.from_orm(obj) for obj in objs]

async def create_invoice(db: AsyncSession, invoice_in: InvoiceCreate) -> InvoiceResponse:
    obj = await crud_invoice.create_invoice(db, invoice_in)
    return InvoiceResponse.from_orm(obj)

async def update_invoice(
    db: AsyncSession, invoice_id: int, invoice_in: InvoiceUpdate
) -> Optional[InvoiceResponse]:
    obj = await crud_invoice.get_invoice(db, invoice_id)
    if not obj:
        return None
    updated = await crud_invoice.update_invoice(db, obj, invoice_in)
    return InvoiceResponse.from_orm(updated)

async def delete_invoice(db: AsyncSession, invoice_id: int) -> bool:
    obj = await crud_invoice.get_invoice(db, invoice_id)
    if not obj:
        return False
    await crud_invoice.delete_invoice(db, invoice_id)
    return True