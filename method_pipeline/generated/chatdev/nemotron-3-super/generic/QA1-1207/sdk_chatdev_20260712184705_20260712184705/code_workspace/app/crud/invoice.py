from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.models import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate

async def get_invoice(db: AsyncSession, invoice_id: int) -> Optional[Invoice]:
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    return result.scalar_one_or_none()

async def get_invoice_by_order(db: AsyncSession, order_id: int) -> Optional[Invoice]:
    result = await db.execute(
        select(Invoice).where(Invoice.order_id == order_id)
    )
    return result.scalar_one_or_none()

async def get_invoices(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Invoice]:
    result = await db.execute(select(Invoice).offset(skip).limit(limit))
    return result.scalars().all()

async def create_invoice(db: AsyncSession, invoice_in: InvoiceCreate) -> Invoice:
    db_obj = Invoice(**invoice_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_invoice(
    db: AsyncSession, db_obj: Invoice, invoice_in: InvoiceUpdate
) -> Invoice:
    update_data = invoice_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_invoice(db: AsyncSession, invoice_id: int) -> Optional[Invoice]:
    obj = await get_invoice(db, invoice_id)
    if obj:
        await db.delete(obj)
        await db.commit()
    return obj