"""
Payment repository for database operations
"""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.tables import PaymentTable
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[PaymentTable]):
    """Repository for Payment entity"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, PaymentTable)
    
    async def get_by_id(self, id: str) -> Optional[PaymentTable]:
        """Get payment by ID"""
        return await self.get(id)
    
    async def get_by_order_ref(self, order_ref: str) -> Optional[PaymentTable]:
        """Get payment by order reference"""
        result = await self.session.execute(
            select(PaymentTable).where(PaymentTable.order_ref == order_ref)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[PaymentTable]:
        """Get all payments"""
        return await self.list_all(limit, offset)
    
    async def create_payment(
        self,
        order_ref: str,
        amount: Decimal,
        method: str,
        status: str = "PENDING",
    ) -> PaymentTable:
        """Create a new payment"""
        from app.db.tables import generate_uuid
        from datetime import datetime
        entity = PaymentTable(
            id=generate_uuid(),
            order_ref=order_ref,
            amount=amount,
            timestamp=datetime.utcnow(),
            status=status,
            method=method,
        )
        return await self.create(entity)
    
    async def update_status(self, payment_id: str, status: str) -> Optional[PaymentTable]:
        """Update payment status"""
        return await self.update(payment_id, status=status)
