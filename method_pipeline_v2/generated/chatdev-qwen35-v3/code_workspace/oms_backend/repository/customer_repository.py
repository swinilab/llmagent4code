"""
Customer repository with CRUD operations
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms_backend.domain.models import Customer, CustomerRole
from oms_backend.domain.schemas import CustomerCreate


class CustomerRepository:
    """Repository for Customer entity operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: CustomerCreate) -> Customer:
        """Create a new customer"""
        customer = Customer(
            name=data.name,
            address=data.address,
            phone=data.phone,
            banking_details={
                "accountNumber": data.bankingDetails.accountNumber,
                "bankName": data.bankingDetails.bankName
            },
            role=data.role,
            order_history=[]
        )
        self.session.add(customer)
        await self.session.flush()
        return customer
    
    async def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """Get all customers with pagination"""
        result = await self.session.execute(
            select(Customer).offset(offset).limit(limit)
        )
        return result.scalars().all()
    
    async def update(self, customer_id: str, data: dict) -> Optional[Customer]:
        """Update customer fields"""
        await self.session.execute(
            update(Customer)
            .where(Customer.id == customer_id)
            .values(**data, updated_at=datetime.utcnow())
        )
        return await self.get_by_id(customer_id)
    
    async def add_to_order_history(self, customer_id: str, order_id: str) -> bool:
        """Add order ID to customer's order history"""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return False
        
        if order_id not in customer.order_history:
            customer.order_history.append(order_id)
            customer.updated_at = datetime.utcnow()
            await self.session.flush()
        return True
    
    async def delete(self, customer_id: str) -> bool:
        """Soft delete customer (mark as deleted)"""
        customer = await self.get_by_id(customer_id)
        if customer:
            await self.session.delete(customer)
            return True
        return False
