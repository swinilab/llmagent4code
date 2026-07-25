"""
Invoice repository for database operations
"""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.tables import InvoiceTable
from app.repositories.base_repository import BaseRepository


class InvoiceRepository(BaseRepository[InvoiceTable]):
    """Repository for Invoice entity"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, InvoiceTable)
    
    async def get_by_id(self, id: str) -> Optional[InvoiceTable]:
        """Get invoice by ID"""
        return await self.get(id)
    
    async def get_by_order_ref(self, order_ref: str) -> Optional[InvoiceTable]:
        """Get invoice by order reference"""
        result = await self.session.execute(
            select(InvoiceTable).where(InvoiceTable.order_ref == order_ref)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[InvoiceTable]:
        """Get all invoices"""
        return await self.list_all(limit, offset)
    
    async def create_invoice(
        self,
        order_ref: str,
        billing_name: str,
        billing_address: str,
        total_amount: Decimal,
        issue_date: str,
        due_date: str,
        status: str = "ISSUED",
    ) -> InvoiceTable:
        """Create a new invoice"""
        from app.db.tables import generate_uuid
        entity = InvoiceTable(
            id=generate_uuid(),
            order_ref=order_ref,
            billing_name=billing_name,
            billing_address=billing_address,
            total_amount=total_amount,
            issue_date=issue_date,
            due_date=due_date,
            status=status,
        )
        return await self.create(entity)
    
    async def update_status(self, invoice_id: str, status: str) -> Optional[InvoiceTable]:
        """Update invoice status"""
        return await self.update(invoice_id, status=status)
