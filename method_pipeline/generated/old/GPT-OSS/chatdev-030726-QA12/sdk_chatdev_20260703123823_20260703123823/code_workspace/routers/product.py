"""FastAPI router for product endpoints.
Versioned under /api/{API_VERSION}/products.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import ProductCreate, ProductRead
from services import ProductService
from database import get_db
from config import get_settings

settings = get_settings()
router = APIRouter(prefix=f"/api/{settings.API_VERSION}/products", tags=["products"])

@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    service = ProductService(db)
    try:
        prod = service.create_product(payload.dict())
        return prod
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    service = ProductService(db)
    prod = service.get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod