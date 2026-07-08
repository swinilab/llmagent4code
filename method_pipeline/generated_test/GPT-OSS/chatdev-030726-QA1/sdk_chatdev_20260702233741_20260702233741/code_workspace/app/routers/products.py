# app/routers/products.py
"""Product CRUD endpoints (limited to create and read for demo)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, services, database

router = APIRouter(prefix="/api/v1/products", tags=["products"])

@router.post("/", response_model=schemas.ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    svc = services.ProductService(db)
    return svc.create_product(payload)

@router.get("/{product_id}", response_model=schemas.ProductRead)
def get_product(product_id: int, db: Session = Depends(database.get_db)):
    svc = services.ProductService(db)
    prod = svc.get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod
