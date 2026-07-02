"""
Invoice repository for invoice-specific database operations.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Invoice, InvoiceStatus
from oms.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """
    Repository for Invoice entity operations.
    
    Extends BaseRepository with invoice-specific queries including status filtering,
    order lookups, and overdue detection.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize invoice repository.
        
        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(Invoice, session)
    
    async def get_by_order(self, order_id: int) -> Optional[Invoice]:
        """
        Get invoice by order ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Invoice instance or None if not found
        """
        query = select(Invoice).where(Invoice.order_id == order_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """
        Get invoice by invoice number.
        
        Args:
            invoice_number: Unique invoice number
            
        Returns:
            Invoice instance or None if not found
        """
        query = select(Invoice).where(Invoice.invoice_number == invoice_number)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_invoices_by_status(
        self, status: InvoiceStatus, limit: int = 100, offset: int = 0
    ) -> List[Invoice]:
        """
        Get invoices by status.
        
        Args:
            status: Invoice status to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of invoice instances with the specified status
        """
        query = select(Invoice).where(
            Invoice.status == status
        ).order_by(
            Invoice.created_at.desc()
        ).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_overdue_invoices(self, current_date: datetime, limit: int = 100) -> List[Invoice]:
        """
        Get invoices that are past their due date and not paid.
        
        Args:
            current_date: Current date for comparison
            limit: Maximum number of records to return
            
        Returns:
            List of overdue invoice instances
        """
        query = select(Invoice).where(
            Invoice.due_date < current_date
        ).where(
            Invoice.status != InvoiceStatus.PAID
        ).where(
            Invoice.status != InvoiceStatus.CANCELLED
        ).order_by(
            Invoice.due_date.asc()
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_invoices_in_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> List[Invoice]:
        """
        Get invoices within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of results
            
        Returns:
            List of invoices within the date range
        """
        query = select(Invoice).where(
            Invoice.issue_date >= start_date
        ).where(
            Invoice.issue_date <= end_date
        ).order_by(
            Invoice.issue_date.desc()
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_total_invoiced_amount(self) -> float:
        """
        Calculate total invoiced amount.
        
        Returns:
            Total invoiced amount
        """
        from sqlalchemy import func
        query = select(func.sum(Invoice.total_amount))
        result = await self.session.execute(query)
        return float(result.scalar() or 0)
    
    async def get_total_paid_amount(self) -> float:
        """
        Calculate total paid invoice amount.
        
        Returns:
            Total paid amount
        """
        from sqlalchemy import func
        query = select(func.sum(Invoice.total_amount)).where(
            Invoice.status == InvoiceStatus.PAID
        )
        result = await self.session.execute(query)
        return float(result.scalar() or 0)
