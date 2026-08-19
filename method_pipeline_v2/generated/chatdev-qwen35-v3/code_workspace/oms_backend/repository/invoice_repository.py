"""
Invoice repository with CRUD operations
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms_backend.domain.models import Invoice, InvoiceStatus
from oms_backend.domain.schemas import InvoiceCreate


class InvoiceRepository:
    """Repository for Invoice entity operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: InvoiceCreate) -> Invoice:
        """Create a new invoice"""
        invoice = Invoice(
            order_ref=data.orderRef,
            billing_info={
                "name": data.billingInfo.name,
                "address": data.billingInfo.address
            },
            total_amount=data.totalAmount,
            issue_date=data.issueDate,
            due_date=data.dueDate,
            status=InvoiceStatus.ISSUED
        )
        self.session.add(invoice)
        await self.session.flush()
        return invoice
    
    async def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID"""
        result = await self.session.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_order_ref(self, order_ref: str) -> Optional[Invoice]:
        """Get invoice by order reference"""
        result = await self.session.execute(
            select(Invoice).where(Invoice.order_ref == order_ref)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """Get all invoices with pagination"""
        result = await self.session.execute(
            select(Invoice).offset(offset).limit(limit)
        )
        return result.scalars().all()
    
    async def update_status(self, invoice_id: str, new_status: InvoiceStatus) -> Optional[Invoice]:
        """Update invoice status"""
        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            return None
        
        # State machine validation
        valid_transitions = {
            InvoiceStatus.ISSUED: [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.OVERDUE],
            InvoiceStatus.PAID: [],
            InvoiceStatus.OVERDUE: [InvoiceStatus.PAID, InvoiceStatus.CANCELLED],
            InvoiceStatus.CANCELLED: [],
        }
        
        if new_status not in valid_transitions.get(invoice.status, []):
            raise ValueError(f"Invalid status transition from {invoice.status} to {new_status}")
        
        invoice.status = new_status
        await self.session.flush()
        return invoice
    
    async def update(self, invoice_id: str, data: dict) -> Optional[Invoice]:
        """Update invoice fields"""
        await self.session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(**data)
        )
        return await self.get_by_id(invoice_id)
    
    async def delete(self, invoice_id: str) -> bool:
        """Delete invoice"""
        invoice = await self.get_by_id(invoice_id)
        if invoice:
            await self.session.delete(invoice)
            return True
        return False
