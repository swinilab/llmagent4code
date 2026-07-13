from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate

class ProductService:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository

    def get(self, id: int):
        return self.product_repository.get(id)

    def get_multi(self, skip: int = 0, limit: int = 100):
        return self.product_repository.get_multi(skip, limit)

    def create(self, obj_in: ProductCreate):
        return self.product_repository.create(obj_in)

    def update(self, id: int, obj_in: ProductUpdate):
        obj = self.product_repository.get(id)
        if obj:
            return self.product_repository.update(obj, obj_in)
        return None

    def delete(self, id: int):
        return self.product_repository.remove(id)