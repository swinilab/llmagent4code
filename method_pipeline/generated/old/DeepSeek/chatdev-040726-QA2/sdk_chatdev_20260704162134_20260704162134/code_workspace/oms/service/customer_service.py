"""
Customer service: registration and lookup.
"""

from uuid import UUID

from oms.domain.models import Customer, CreateCustomerRequest
from oms.repository.in_memory import InMemoryCustomerRepository


class CustomerService:
    """Business logic for Customer operations."""

    def __init__(self, repo: InMemoryCustomerRepository) -> None:
        self._repo = repo

    def register(self, request: CreateCustomerRequest) -> Customer:
        """Register a new customer."""
        customer = Customer(
            name=request.name,
            address=request.address,
            phone=request.phone,
            banking_details=request.banking_details,
        )
        return self._repo.save(customer)

    def get_by_id(self, customer_id: UUID) -> Customer | None:
        """Retrieve a customer by ID."""
        return self._repo.find_by_id(customer_id)

    def list_all(self) -> list[Customer]:
        """List all registered customers."""
        return self._repo.find_all()
