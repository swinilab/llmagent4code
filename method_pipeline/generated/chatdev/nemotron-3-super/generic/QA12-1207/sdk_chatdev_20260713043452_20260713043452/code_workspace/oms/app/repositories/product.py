from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int):
        return self.db.query(Product).filter(Product.id == id).first()

    def get_multi(self, skip: int = 0, limit: int = 100):
        return self.db.query(Product).offset(skip).limit(limit).all()

    def create(self, obj_in: ProductCreate):
        db_obj = Product(
            description=obj_in.description,
            base_price=obj_in.base_price,
            currency=obj_in.currency
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Product, obj_in: ProductUpdate):
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def remove(self, id: int):
        obj = self.db.query(Product).get(id)
        self.db.delete(obj)
        self.db.commit()
        return obj