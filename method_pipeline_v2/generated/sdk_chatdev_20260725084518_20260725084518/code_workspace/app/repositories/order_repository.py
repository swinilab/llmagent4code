"""
Order repository for database operations
"""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.tables import OrderTable
from app.repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository[OrderTable]):
    """Repository for Order entity"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, OrderTable)
    
    async def get_by_id(self, id: str) -> Optional[OrderTable]:
        """Get order by ID"""
        return await self.get(id)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[OrderTable]:
        """Get all orders"""
        return await self.list_all(limit, offset)
    
    async def get_most_recent(self, limit: int = 1) -> List[OrderTable]:
        """Get most recent orders"""
        result = await self.session.execute(
            select(OrderTable).order_by(OrderTable.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_order(
        self,
        customer_ref: str,
        line_items: list,
        total_amount: Decimal,
        status: str = "PLACED",
    ) -> OrderTable:
        """Create a new order"""
        from app.db.tables import generate_uuid
        entity = OrderTable(
            id=generate_uuid(),
            customer_ref=customer_ref,
            line_items=line_items,
            total_amount=total_amount,
            status=status,
        )
        return await self.create(entity)
    
    async def update_status(self, order_id: str, status: str) -> Optional[OrderTable]:
        """Update order status"""
        from datetime import datetime
        return await self.update(order_id, status=status, updated_at=datetime.utcnow())
    
    async def set_invoice_ref(self, order_id: str, invoice_ref: str) -> Optional[OrderTable]:
        """Set invoice reference for order"""
        from datetime import datetime
        return await self.update(order_id, invoice_ref=invoice_ref, updated_at=datetime.utcnow())
