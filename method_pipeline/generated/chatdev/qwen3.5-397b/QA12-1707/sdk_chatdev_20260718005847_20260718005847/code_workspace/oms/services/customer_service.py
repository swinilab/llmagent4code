"""
Customer service for business logic operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from oms.models.customer import Customer, CustomerCreate, CustomerUpdate, CustomerResponse
from oms.repositories.customer_repository import CustomerRepository


class CustomerService:
    """
    Service for Customer business logic.
    Handles validation, business rules, and orchestration.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = CustomerRepository(session)
    
    async def get_customer(self, customer_id: int) -> Optional[CustomerResponse]:
        """Get a customer by ID."""
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            return None
        return CustomerResponse.model_validate(customer)
    
    async def get_customer_by_email(self, email: str) -> Optional[CustomerResponse]:
        """Get a customer by email."""
        customer = await self.repository.get_by_email(email)
        if not customer:
            return None
        return CustomerResponse.model_validate(customer)
    
    async def get_all_customers(self, skip: int = 0, limit: int = 100) -> List[CustomerResponse]:
        """Get all customers with pagination."""
        customers = await self.repository.get_all(skip=skip, limit=limit)
        return [CustomerResponse.model_validate(c) for c in customers]
    
    async def create_customer(self, customer_data: CustomerCreate) -> CustomerResponse:
        """Create a new customer."""
        existing = await self.repository.get_by_email(customer_data.email)
        if existing:
            raise ValueError(f"Customer with email {customer_data.email} already exists")
        
        customer = await self.repository.create(customer_data)
        return CustomerResponse.model_validate(customer)
    
    async def update_customer(self, customer_id: int, customer_data: CustomerUpdate) -> Optional[CustomerResponse]:
        """Update an existing customer."""
        if customer_data.email:
            existing = await self.repository.get_by_email(customer_data.email)
            if existing and existing.id != customer_id:
                raise ValueError(f"Customer with email {customer_data.email} already exists")
        
        customer = await self.repository.update(customer_id, customer_data)
        if not customer:
            return None
        return CustomerResponse.model_validate(customer)
    
    async def delete_customer(self, customer_id: int) -> bool:
        """Delete a customer."""
        return await self.repository.delete(customer_id)
    
    async def get_customer_count(self) -> int:
        """Get total number of customers."""
        return await self.repository.count()
