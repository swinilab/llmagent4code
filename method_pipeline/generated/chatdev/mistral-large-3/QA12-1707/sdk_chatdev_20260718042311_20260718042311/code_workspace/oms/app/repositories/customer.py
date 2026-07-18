"""
Customer repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate


class CustomerRepository:
    """Customer repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, customer: CustomerCreate) -> Customer:
        """Create a new customer."""
        db_customer = Customer(**customer.model_dump())
        self.db.add(db_customer)
        self.db.commit()
        self.db.refresh(db_customer)
        return db_customer

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        """Get customer by ID."""
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def list_all(self) -> list[Customer]:
        """List all customers."""
        return self.db.query(Customer).all()