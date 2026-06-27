"""
Customer Controller - Handles HTTP request/response for Customer operations.
Coordinates between routes and services.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
    CustomerListResponse,
)
from services.customer_service import CustomerService


class CustomerController:
    """Controller class for Customer HTTP operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the controller with a database session."""
        self.service = CustomerService(db_session)

    async def get_customer(self, customer_id: int) -> Optional[Customer]:
        """
        Get a single customer by ID.
        
        Args:
            customer_id: The unique customer ID
            
        Returns:
            Customer object if found, None otherwise
        """
        return await self.service.get_customer_by_id(customer_id)

    async def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """
        Get a customer by email.
        
        Args:
            email: Customer email address
            
        Returns:
            Customer object if found, None otherwise
        """
        return await self.service.get_customer_by_email(email)

    async def get_all_customers(
        self, skip: int = 0, limit: int = 100
    ) -> CustomerListResponse:
        """
        Get all customers with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            CustomerListResponse with customers and total count
        """
        customers = await self.service.get_all_customers(skip=skip, limit=limit)
        total = await self.service.get_customer_count()
        return CustomerListResponse(customers=customers, total=total)

    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """
        Create a new customer.
        
        Args:
            customer_data: CustomerCreate object with customer information
            
        Returns:
            Created Customer object
        """
        return await self.service.create_customer(customer_data)

    async def update_customer(
        self, customer_id: int, customer_data: CustomerUpdate
    ) -> Optional[Customer]:
        """
        Update an existing customer.
        
        Args:
            customer_id: The unique customer ID
            customer_data: CustomerUpdate object with updated information
            
        Returns:
            Updated Customer object if found, None otherwise
        """
        return await self.service.update_customer(customer_id, customer_data)

    async def delete_customer(self, customer_id: int) -> bool:
        """
        Delete a customer.
        
        Args:
            customer_id: The unique customer ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        return await self.service.delete_customer(customer_id)
