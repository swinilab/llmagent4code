"""
OMS Customer Service - Business logic for customer management.
"""
from typing import List, Optional
import uuid
from app.domain.entities.models import Customer, UserRole
from app.domain.repositories.interfaces import CustomerRepository


class CustomerService:
    """Service for customer operations."""

    def __init__(self, customer_repo: CustomerRepository):
        self._repo = customer_repo

    def create_customer(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.CUSTOMER
    ) -> Customer:
        """Create a new customer."""
        existing = self._repo.find_by_email(email)
        if existing:
            raise ValueError(f"Customer with email {email} already exists")
        
        customer = Customer(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            phone=phone,
            role=role
        )
        return self._repo.save(customer)

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        return self._repo.find_by_id(customer_id)

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """Get customer by email."""
        return self._repo.find_by_email(email)

    def list_customers_by_role(self, role: UserRole) -> List[Customer]:
        """List customers by role."""
        return self._repo.find_by_role(role.value)

    def list_active_customers(self) -> List[Customer]:
        """List all active customers."""
        return self._repo.find_active()

    def update_customer(self, customer_id: str, data: dict) -> Optional[Customer]:
        """Update customer information."""
        customer = self._repo.find_by_id(customer_id)
        if not customer:
            return None
        
        if 'email' in data:
            existing = self._repo.find_by_email(data['email'])
            if existing and existing.id != customer_id:
                raise ValueError(f"Customer with email {data['email']} already exists")
        
        return self._repo.update(customer_id, data)

    def deactivate_customer(self, customer_id: str) -> Optional[Customer]:
        """Deactivate a customer."""
        return self._repo.update(customer_id, {'is_active': False})

    def activate_customer(self, customer_id: str) -> Optional[Customer]:
        """Activate a customer."""
        return self._repo.update(customer_id, {'is_active': True})
