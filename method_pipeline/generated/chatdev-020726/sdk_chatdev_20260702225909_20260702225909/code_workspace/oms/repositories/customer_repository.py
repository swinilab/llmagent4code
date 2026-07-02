"""
Customer repository for customer-specific database operations.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Customer
from oms.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """
    Repository for Customer entity operations.
    
    Extends BaseRepository with customer-specific queries.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize customer repository.
        
        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(Customer, session)
    
    async def get_by_email(self, email: str) -> Optional[Customer]:
        """
        Get customer by email address.
        
        Args:
            email: Customer email address
            
        Returns:
            Customer instance or None if not found
        """
        query = select(Customer).where(Customer.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_customers(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """
        Get all active customers with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of active customer instances
        """
        query = select(Customer).where(Customer.is_active == True).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def search_by_name(self, name_pattern: str, limit: int = 50) -> List[Customer]:
        """
        Search customers by name pattern.
        
        Args:
            name_pattern: Name pattern to search for
            limit: Maximum number of results
            
        Returns:
            List of matching customer instances
        """
        query = select(Customer).where(
            Customer.name.ilike(f"%{name_pattern}%")
        ).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
