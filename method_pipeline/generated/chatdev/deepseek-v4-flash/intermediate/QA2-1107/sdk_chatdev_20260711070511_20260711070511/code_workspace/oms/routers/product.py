"""
Product REST router.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from oms.database import get_db
from oms.models.entities import ProductModel
from oms.repositories.product_repo import ProductRepository
from oms.schemas.product import ProductCreate, ProductResponse, ProductUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    entity = ProductModel(**data.model_dump())
    repo.create(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.get("", response_model=List[ProductResponse])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    return repo.list_all(skip, limit)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    entity = repo.get(product_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Product not found")
    return entity


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str, data: ProductUpdate, db: Session = Depends(get_db)
):
    repo = ProductRepository(db)
    entity = repo.get(product_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return entity
    updated = repo.update_with_optimistic_lock(product_id, updates, entity.version)
    if updated is None:
        raise HTTPException(status_code=409, detail="Concurrent modification detected")
    db.commit()
    return updated


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: str, db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    if not repo.delete(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    db.commit()
