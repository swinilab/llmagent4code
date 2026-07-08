"""
Base repository providing common CRUD operations.
"""

from sqlalchemy.orm import Session
from typing import TypeVar, Generic, List, Type, Optional

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: ModelType, obj_in: dict) -> ModelType:
        """Update fields of an existing model instance."""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    def delete(self, db: Session, id: int) -> ModelType:
        """Delete a record by its primary key.

        Returns the deleted instance or raises a ``ValueError`` if the record
        does not exist.  Using ``filter(...).first()`` works with SQLAlchemy 2.0
        and avoids the removed ``Query.get`` method.
        """
        obj = db.query(self.model).filter(self.model.id == id).first()
        if obj is None:
            raise ValueError(f"{self.model.__name__} with id {id} not found")
        db.delete(obj)
        db.commit()
        return obj
