from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate

class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int):
        return self.db.query(Customer).filter(Customer.id == id).first()

    def get_by_name(self, name: str):
        return self.db.query(Customer).filter(Customer.name == name).first()

    def get_multi(self, skip: int = 0, limit: int = 100):
        return self.db.query(Customer).offset(skip).limit(limit).all()

    def create(self, obj_in: CustomerCreate):
        db_obj = Customer(
            name=obj_in.name,
            address=obj_in.address,
            phone=obj_in.phone,
            banking_details=obj_in.banking_details,
            role=obj_in.role
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Customer, obj_in: CustomerUpdate):
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def remove(self, id: int):
        obj = self.db.query(Customer).get(id)
        self.db.delete(obj)
        self.db.commit()
        return obj