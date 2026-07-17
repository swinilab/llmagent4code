"""
Invoice repository for data access operations.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms.models.invoice import Invoice, InvoiceStatus, InvoiceCreate


class InvoiceRepository:
    """
    Repository for Invoice entity operations.
    Provides CRUD operations with async support.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Get an invoice by ID."""
        result = await self.session.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_order_id(self, order_id: int) -> Optional[Invoice]:
        """Get an invoice by order ID."""
        result = await self.session.execute(
            select(Invoice).where(Invoice.order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(self, status: InvoiceStatus, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Get invoices by status."""
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Get all invoices with pagination."""
        result = await self.session.execute(
            select(Invoice).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, invoice_data: InvoiceCreate, subtotal: float, total: float) -> Invoice:
        """Create a new invoice."""
        from datetime import datetime, timedelta
        
        invoice = Invoice(
            order_id=invoice_data.order_id,
            billing_name=invoice_data.billing_name,
            billing_address=invoice_data.billing_address,
            subtotal=subtotal,
            tax_amount=total - subtotal,
            total_amount=total,
            currency="USD",
            status=InvoiceStatus.DRAFT,
            notes=invoice_data.notes,
        )
        self.session.add(invoice)
        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice
    
    async def update_status(self, invoice_id: int, status: InvoiceStatus) -> Optional[Invoice]:
        """Update invoice status."""
        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            return None
        
        invoice.status = status
        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice
    
    async def issue(self, invoice_id: int, issue_date: Optional[datetime] = None, 
                    due_date: Optional[datetime] = None) -> Optional[Invoice]:
        """Issue an invoice."""
        from datetime import datetime, timedelta
        
        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            return None
        
        invoice.issue_date = issue_date or datetime.utcnow()
        invoice.due_date = due_date or (invoice.issue_date + timedelta(days=30))
        invoice.status = InvoiceStatus.ISSUED
        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice
    
    async def update(self, invoice_id: int, **kwargs) -> Optional[Invoice]:
        """Update an invoice."""
        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            return None
        
        for field, value in kwargs.items():
            setattr(invoice, field, value)
        
        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice
    
    async def delete(self, invoice_id: int) -> bool:
        """Delete an invoice by ID."""
        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            return False
        
        await self.session.delete(invoice)
        await self.session.flush()
        return True
    
    async def count(self) -> int:
        """Get total number of invoices."""
        result = await self.session.execute(select(func.count()).select_from(Invoice))
        return result.scalar() or 0
