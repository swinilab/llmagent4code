"""
Customer service layer.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerRead


class CustomerService:
    """Customer service."""

    def __init__(self, db: Session):
        self.repo = CustomerRepository(db)

    def create_customer(self, customer: CustomerCreate) -> CustomerRead:
        """Create a new customer."""
        db_customer = self.repo.create(customer)
        return CustomerRead.model_validate(db_customer)

    def get_customer(self, customer_id: int) -> Optional[CustomerRead]:
        """Get customer by ID."""
        db_customer = self.repo.get_by_id(customer_id)
        if not db_customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return CustomerRead.model_validate(db_customer)

    def list_customers(self) -> list[CustomerRead]:
        """List all customers."""
        db_customers = self.repo.list_all()
        return [CustomerRead.model_validate(customer) for customer in db_customers]