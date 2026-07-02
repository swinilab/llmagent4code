"""
Customer service handling business logic.
"""

from sqlalchemy.orm import Session
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate

class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CustomerRepository()

    def create_customer(self, payload: CustomerCreate):
        return self.repo.create(self.db, payload.model_dump())

    def get_customer(self, customer_id: int):
        return self.repo.get(self.db, customer_id)

    def update_customer(self, customer_id: int, payload: CustomerUpdate):
        db_obj = self.repo.get(self.db, customer_id)
        if not db_obj:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        return self.repo.update(self.db, db_obj, update_data)

    def delete_customer(self, customer_id: int):
        return self.repo.delete(self.db, customer_id)
