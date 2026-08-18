"""
Customer service with business logic and validation
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from oms.repository.customer_repository import CustomerRepository
from oms.domain.models import Customer, CustomerCreate
from oms.infrastructure.exceptions import NotFoundException, ValidationException
from oms.infrastructure.cache.memory_cache import MemoryCache
from oms.infrastructure.database import transaction_session


class CustomerService:
    """
    Customer service implementing business logic
    Implements NFR 1.2 via cache integration
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = CustomerRepository(session)
        self.cache = MemoryCache.get_instance()
    
    async def get_by_id(self, customer_id: str) -> Customer:
        """Get customer by ID with cache lookup"""
        # Try cache first (NFR 1.2)
        cached = await self.cache.get(f"customer:{customer_id}")
        if cached:
            return Customer(**cached)
        
        # Fallback to database
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            raise NotFoundException(f"Customer {customer_id} not found")
        
        # Populate cache
        await self.cache.set(f"customer:{customer_id}", customer.model_dump())
        return customer
    
    async def get_all(self) -> List[Customer]:
        """Get all customers"""
        return await self.repository.get_all()
    
    async def create(self, customer: CustomerCreate) -> Customer:
        """Create new customer"""
        async with transaction_session() as session:
            # Create repository with the transaction session
            customer_repo = CustomerRepository(session)
            created = await customer_repo.create(customer)
            # Populate cache
            await self.cache.set(f"customer:{created.id}", created.model_dump())
            return created
    
    async def update(self, customer_id: str, customer: CustomerCreate) -> Customer:
        """Update existing customer"""
        async with transaction_session() as session:
            # Create repository with the transaction session
            customer_repo = CustomerRepository(session)
            # Invalidate cache
            await self.cache.delete(f"customer:{customer_id}")
            
            updated = await customer_repo.update(customer_id, customer)
            if not updated:
                raise NotFoundException(f"Customer {customer_id} not found")
            
            # Populate cache
            await self.cache.set(f"customer:{customer_id}", updated.model_dump())
            return updated
    
    async def delete(self, customer_id: str) -> bool:
        """Delete customer"""
        # Invalidate cache
        await self.cache.delete(f"customer:{customer_id}")
        return await self.repository.delete(customer_id)
    
    async def add_to_order_history(self, customer_id: str, order_id: str) -> None:
        """Add order to customer's order history"""
        await self.repository.add_to_order_history(customer_id, order_id)
        # Invalidate cache to refresh order history
        await self.cache.delete(f"customer:{customer_id}")
