"""
Customer repository for data access operations.
"""

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from oms.models.customer import Customer, CustomerCreate, CustomerUpdate


class CustomerRepository:
    """
    Repository for Customer entity operations.
    Provides CRUD operations with async support.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, customer_id: int) -> Optional[Customer]:
        """Get a customer by ID."""
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[Customer]:
        """Get a customer by email."""
        result = await self.session.execute(
            select(Customer).where(Customer.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        """Get all customers with pagination."""
        result = await self.session.execute(
            select(Customer).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer."""
        customer = Customer(**customer_data.model_dump())
        self.session.add(customer)
        await self.session.flush()
        await self.session.refresh(customer)
        return customer
    
    async def update(self, customer_id: int, customer_data: CustomerUpdate) -> Optional[Customer]:
        """Update an existing customer."""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None
        
        update_data = customer_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        
        await self.session.flush()
        await self.session.refresh(customer)
        return customer
    
    async def delete(self, customer_id: int) -> bool:
        """Delete a customer by ID."""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return False
        
        await self.session.delete(customer)
        await self.session.flush()
        return True
    
    async def count(self) -> int:
        """Get total number of customers."""
        from sqlalchemy import func
        result = await self.session.execute(select(func.count()).select_from(Customer))
        return result.scalar() or 0
