from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.app.db.session import get_db
from oms_backend.app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from oms_backend.app.services import product_service

router = APIRouter()

@router.get("/", response_model=list[ProductResponse])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = product_service.get_products(db, skip=skip, limit=limit)
    return products

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    return product_service.create_product(db, product_in)

@router.get("/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_obj = product_service.get_product(db, product_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_obj

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    db_obj = product_service.get_product(db, product_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Product not found")
    updated = product_service.update_product(db, product_id, product_in)
    return updated

@router.delete("/{product_id}", response_model=ProductResponse)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_obj = product_service.get_product(db, product_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Product not found")
    deleted = product_service.delete_product(db, db_obj.id)
    return deleted