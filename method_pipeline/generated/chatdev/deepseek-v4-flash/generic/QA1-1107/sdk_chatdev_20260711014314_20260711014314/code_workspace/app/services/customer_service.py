"""
Service layer for Customer entity.
Handles business logic, validation, and transaction boundaries.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Business logic for customer operations."""

    @staticmethod
    async def create(db: AsyncSession, data: CustomerCreate) -> Customer:
        """Create a new customer."""
        customer = Customer(**data.model_dump())
        db.add(customer)
        await db.flush()
        return customer

    @staticmethod
    async def get_by_id(db: AsyncSession, customer_id: str) -> Optional[Customer]:
        """Retrieve a customer by ID."""
        result = await db.execute(select(Customer).where(Customer.id == customer_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Customer]:
        """List customers with pagination."""
        result = await db.execute(
            select(Customer).offset(skip).limit(limit).order_by(Customer.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, customer_id: str, data: CustomerUpdate) -> Optional[Customer]:
        """Update a customer's details."""
        customer = await CustomerService.get_by_id(db, customer_id)
        if not customer:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        await db.flush()
        # Refresh to load server-side defaults (updated_at)
        await db.refresh(customer)
        return customer

    @staticmethod
    async def delete(db: AsyncSession, customer_id: str) -> bool:
        """Delete a customer by ID."""
        customer = await CustomerService.get_by_id(db, customer_id)
        if not customer:
            return False
        await db.delete(customer)
        await db.flush()
        return True
