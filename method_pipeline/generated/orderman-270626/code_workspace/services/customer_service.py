"""
Customer Service - Business logic for Customer operations.
Handles all customer-related business operations.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import CustomerModel, UserRoleEnum
from shared.models import Customer, CustomerCreate, CustomerUpdate, UserRole


class CustomerService:
    """Service class for Customer business operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db_session

    async def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """
        Get a customer by their unique identifier.
        
        Args:
            customer_id: The unique customer ID
            
        Returns:
            Customer object if found, None otherwise
        """
        result = await self.db.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if customer:
            return self._to_domain_model(customer)
        return None

    async def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """
        Get a customer by their email address.
        
        Args:
            email: Customer email address
            
        Returns:
            Customer object if found, None otherwise
        """
        result = await self.db.execute(
            select(CustomerModel).where(CustomerModel.email == email)
        )
        customer = result.scalar_one_or_none()
        
        if customer:
            return self._to_domain_model(customer)
        return None

    async def get_all_customers(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        """
        Get all customers with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Customer objects
        """
        result = await self.db.execute(
            select(CustomerModel)
            .offset(skip)
            .limit(limit)
        )
        customers = result.scalars().all()
        return [self._to_domain_model(c) for c in customers]

    async def get_customer_count(self) -> int:
        """
        Get the total number of customers.
        
        Returns:
            Total count of customers
        """
        result = await self.db.execute(
            select(func.count()).select_from(CustomerModel)
        )
        return result.scalar() or 0

    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """
        Create a new customer.
        
        Args:
            customer_data: CustomerCreate object with customer information
            
        Returns:
            Created Customer object
        """
        customer = CustomerModel(
            name=customer_data.name,
            address=customer_data.address,
            phone=customer_data.phone,
            email=customer_data.email,
            banking_details=customer_data.banking_details,
            role=UserRoleEnum(customer_data.role.value),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        
        return self._to_domain_model(customer)

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
        result = await self.db.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            return None
        
        # Update fields if provided
        if customer_data.name is not None:
            customer.name = customer_data.name
        if customer_data.address is not None:
            customer.address = customer_data.address
        if customer_data.phone is not None:
            customer.phone = customer_data.phone
        if customer_data.email is not None:
            customer.email = customer_data.email
        if customer_data.banking_details is not None:
            customer.banking_details = customer_data.banking_details
        if customer_data.role is not None:
            customer.role = UserRoleEnum(customer_data.role.value)
        
        customer.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(customer)
        
        return self._to_domain_model(customer)

    async def delete_customer(self, customer_id: int) -> bool:
        """
        Delete a customer by their ID.
        
        Args:
            customer_id: The unique customer ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        result = await self.db.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            return False
        
        await self.db.delete(customer)
        await self.db.commit()
        return True

    def _to_domain_model(self, customer_model: CustomerModel) -> Customer:
        """
        Convert SQLAlchemy model to domain model.
        
        Args:
            customer_model: SQLAlchemy CustomerModel object
            
        Returns:
            Domain Customer object
        """
        return Customer(
            id=customer_model.id,
            name=customer_model.name,
            address=customer_model.address,
            phone=customer_model.phone,
            email=customer_model.email,
            banking_details=customer_model.banking_details,
            role=UserRole(customer_model.role.value),
            created_at=customer_model.created_at,
            updated_at=customer_model.updated_at,
            order_history=[order.id for order in customer_model.orders],
        )
