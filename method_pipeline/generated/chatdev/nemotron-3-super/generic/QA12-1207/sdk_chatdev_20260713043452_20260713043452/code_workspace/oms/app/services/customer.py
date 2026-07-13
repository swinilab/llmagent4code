from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.models.customer import Customer

class CustomerService:
    def __init__(self, customer_repository: CustomerRepository):
        self.customer_repository = customer_repository

    def get(self, id: int):
        return self.customer_repository.get(id)

    def get_by_name(self, name: str):
        return self.customer_repository.get_by_name(name)

    def get_multi(self, skip: int = 0, limit: int = 100):
        return self.customer_repository.get_multi(skip, limit)

    def create(self, obj_in: CustomerCreate):
        return self.customer_repository.create(obj_in)

    def update(self, id: int, obj_in: CustomerUpdate):
        obj = self.customer_repository.get(id)
        if obj:
            return self.customer_repository.update(obj, obj_in)
        return None

    def delete(self, id: int):
        return self.customer_repository.remove(id)