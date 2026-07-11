"""
Service layer for Customer operations.
"""
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Business logic for managing customers."""

    @staticmethod
    def create(db: Session, data: CustomerCreate, commit: bool = True) -> Customer:
        customer = Customer(**data.model_dump())
        db.add(customer)
        if commit:
            db.commit()
            db.refresh(customer)
        else:
            db.flush()
        return customer

    @staticmethod
    def get_by_id(db: Session, customer_id: str) -> Customer | None:
        return db.query(Customer).filter(Customer.id == customer_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Customer]:
        return db.query(Customer).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, customer_id: str, data: CustomerUpdate, commit: bool = True) -> Customer | None:
        customer = CustomerService.get_by_id(db, customer_id)
        if not customer:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        if commit:
            db.commit()
            db.refresh(customer)
        else:
            db.flush()
        return customer

    @staticmethod
    def delete(db: Session, customer_id: str, commit: bool = True) -> bool:
        customer = CustomerService.get_by_id(db, customer_id)
        if not customer:
            return False
        db.delete(customer)
        if commit:
            db.commit()
        else:
            db.flush()
        return True
