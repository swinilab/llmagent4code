"""
Customer service with business logic
Implements NFR 2.4 (transactions) via async session management
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from oms_backend.repository.customer_repository import CustomerRepository
from oms_backend.domain.models import Customer
from oms_backend.domain.schemas import CustomerCreate, CustomerResponse


class CustomerService:
    """Service for Customer business logic"""
    
    def __init__(self, session: AsyncSession):
        self.repository = CustomerRepository(session)
        self.session = session
    
    async def create_customer(self, data: CustomerCreate) -> Customer:
        """Create a new customer with transactional semantics (NFR 2.4)"""
        customer = await self.repository.create(data)
        return customer
    
    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID with cache check (NFR 1.2)"""
        from oms_backend.repository.base import db
        cache_key = f"customer:{customer_id}"
        cached = db.get_cached(cache_key)
        if cached:
            return cached
        
        customer = await self.repository.get_by_id(customer_id)
        if customer:
            db.set_cached(cache_key, customer)
        return customer
    
    async def get_all_customers(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """Get all customers"""
        return await self.repository.get_all(limit, offset)
    
    async def update_customer(self, customer_id: str, data: dict) -> Optional[Customer]:
        """Update customer with cache invalidation (NFR 1.2)"""
        from oms_backend.repository.base import db
        customer = await self.repository.update(customer_id, data)
        if customer:
            db.set_cached(f"customer:{customer_id}", customer)
        return customer
    
    async def add_order_to_history(self, customer_id: str, order_id: str) -> bool:
        """Add order to customer history"""
        return await self.repository.add_to_order_history(customer_id, order_id)
