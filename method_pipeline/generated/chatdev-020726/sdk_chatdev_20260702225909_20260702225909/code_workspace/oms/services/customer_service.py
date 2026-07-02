"""
Customer service for customer-related business logic.
"""
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Customer
from oms.models.schemas import CustomerCreate, CustomerResponse
from oms.repositories.customer_repository import CustomerRepository


class CustomerService:
    """
    Service for managing customer operations.
    
    Handles business logic for customer creation, retrieval, and management.
    All operations are async and use dependency injection for repositories.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize customer service.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.repository = CustomerRepository(session)
        self.session = session
    
    async def create_customer(self, customer_data: CustomerCreate) -> CustomerResponse:
        """
        Create a new customer.
        
        Args:
            customer_data: Customer creation data
            
        Returns:
            Created customer response
            
        Raises:
            ValueError: If email already exists
        """
        existing = await self.repository.get_by_email(customer_data.email)
        if existing:
            raise ValueError(f"Customer with email {customer_data.email} already exists")
        
        customer = Customer(
            name=customer_data.name,
            email=customer_data.email,
            phone=customer_data.phone,
            address=customer_data.address,
            banking_details=customer_data.banking_details,
        )
        created = await self.repository.create(customer)
        return CustomerResponse.model_validate(created)
    
    async def get_customer(self, customer_id: int) -> Optional[CustomerResponse]:
        """
        Get customer by ID.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer response or None if not found
        """
        customer = await self.repository.get(customer_id)
        if customer is None:
            return None
        return CustomerResponse.model_validate(customer)
    
    async def get_all_customers(
        self, limit: int = 100, offset: int = 0
    ) -> List[CustomerResponse]:
        """
        Get all customers with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of customer responses
        """
        customers = await self.repository.get_all(limit=limit, offset=offset)
        return [CustomerResponse.model_validate(c) for c in customers]
    
    async def get_active_customers(
        self, limit: int = 100, offset: int = 0
    ) -> List[CustomerResponse]:
        """
        Get all active customers.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of active customer responses
        """
        customers = await self.repository.get_active_customers(limit=limit, offset=offset)
        return [CustomerResponse.model_validate(c) for c in customers]
    
    async def search_customers(self, name_pattern: str) -> List[CustomerResponse]:
        """
        Search customers by name.
        
        Args:
            name_pattern: Name pattern to search for
            
        Returns:
            List of matching customer responses
        """
        customers = await self.repository.search_by_name(name_pattern)
        return [CustomerResponse.model_validate(c) for c in customers]
    
    async def update_customer(
        self, customer_id: int, customer_data: CustomerCreate
    ) -> Optional[CustomerResponse]:
        """
        Update an existing customer.
        
        Args:
            customer_id: Customer ID
            customer_data: Updated customer data
            
        Returns:
            Updated customer response or None if not found
        """
        customer = await self.repository.get(customer_id)
        if customer is None:
            return None
        
        customer.name = customer_data.name
        customer.email = customer_data.email
        customer.phone = customer_data.phone
        customer.address = customer_data.address
        customer.banking_details = customer_data.banking_details
        
        updated = await self.repository.update(customer)
        return CustomerResponse.model_validate(updated)
    
    async def delete_customer(self, customer_id: int) -> bool:
        """
        Delete a customer (soft delete by setting is_active to False).
        
        Args:
            customer_id: Customer ID
            
        Returns:
            True if deleted, False if not found
        """
        customer = await self.repository.get(customer_id)
        if customer is None:
            return False
        customer.is_active = False
        await self.repository.update(customer)
        return True
    
    async def hard_delete_customer(self, customer_id: int) -> bool:
        """
        Permanently delete a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(customer_id)
