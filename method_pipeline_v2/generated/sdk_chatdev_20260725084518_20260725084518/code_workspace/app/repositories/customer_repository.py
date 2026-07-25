"""
Customer repository for database operations
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.tables import CustomerTable
from app.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[CustomerTable]):
    """Repository for Customer entity"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, CustomerTable)
    
    async def get_by_id(self, id: str) -> Optional[CustomerTable]:
        """Get customer by ID"""
        return await self.get(id)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[CustomerTable]:
        """Get all customers"""
        return await self.list_all(limit, offset)
    
    async def create_customer(
        self,
        name: str,
        address: str,
        phone: str,
        banking_account_number: str,
        banking_bank_name: str,
        role: str = "CUSTOMER",
    ) -> CustomerTable:
        """Create a new customer"""
        from app.db.tables import generate_uuid
        entity = CustomerTable(
            id=generate_uuid(),
            name=name,
            address=address,
            phone=phone,
            banking_account_number=banking_account_number,
            banking_bank_name=banking_bank_name,
            role=role,
            order_history=[],
        )
        return await self.create(entity)
    
    async def add_to_order_history(self, customer_id: str, order_id: str) -> bool:
        """Add order to customer's order history"""
        customer = await self.get(customer_id)
        if not customer:
            return False
        
        history = customer.order_history or []
        if len(history) >= 10000:
            history = history[-9999:]  # Soft cap
        
        history.append(order_id)
        return await self.update(customer_id, order_history=history) is not None
