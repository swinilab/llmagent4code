"""
Customer Service - business logic for customer management.
"""
import logging
from typing import List, Optional
from datetime import datetime
from datetime import datetime, timezone
from ..domain.models import Customer, Address, BankingDetails, UserRole
from ..infrastructure.repositories import CustomerRepository
from ..infrastructure.database import SessionLocal

logger = logging.getLogger(__name__)


class CustomerService:
    """Service layer for customer operations."""

    def __init__(self, db_session=None):
        self.db_session = db_session
        self._repo = None

    @property
    def repo(self) -> CustomerRepository:
        if self._repo is None:
            if self.db_session:
                self._repo = CustomerRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._repo

    def create_customer(self, name: str, email: str, phone: str = "",
                       address: Optional[Address] = None,
                       banking_details: Optional[BankingDetails] = None,
                       role: UserRole = UserRole.CUSTOMER) -> Customer:
        """Create a new customer."""
        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            address=address,
            banking_details=banking_details,
            role=role
        )
        return self.repo.create(customer)

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        return self.repo.get_by_id(customer_id)

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """Get customer by email."""
        return self.repo.get_by_email(email)

    def update_customer(self, customer_id: str, **kwargs) -> Optional[Customer]:
        """Update customer fields."""
        customer = self.repo.get_by_id(customer_id)
        if not customer:
            return None

        for key, value in kwargs.items():
            if hasattr(customer, key) and value is not None:
                setattr(customer, key, value)

        customer.updated_at = datetime.now(timezone.utc)
        return self.repo.update(customer)
        return self.repo.update(customer)

    def delete_customer(self, customer_id: str) -> bool:
        """Delete a customer."""
        return self.repo.delete(customer_id)

    def list_customers(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        """List all customers."""
        return self.repo.get_all(skip=skip, limit=limit)


def get_customer_service(db_session=None) -> CustomerService:
    """Factory function to get customer service with proper session management."""
    return CustomerService(db_session)
