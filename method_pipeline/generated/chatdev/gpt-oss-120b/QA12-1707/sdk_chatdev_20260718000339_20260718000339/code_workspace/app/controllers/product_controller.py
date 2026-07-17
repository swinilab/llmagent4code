"""FastAPI controller for Product endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..services.product_service import ProductService
from ..database import get_session
from ..models import Product
from pydantic import BaseModel

router = APIRouter(prefix="/products", tags=["products"])

class ProductCreate(BaseModel):
    description: str
    unit_price: float
    currency: str = "USD"
    quantity: int = 0

@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, session: Session = Depends(get_session)):
    product = Product(
        description=payload.description,
        unit_price=payload.unit_price,
        currency=payload.currency,
        quantity=payload.quantity,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

@router.get("/{product_id}", response_model=Product)
def get_product(product_id: int, session: Session = Depends(get_session)):
    product = ProductService.get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/", response_model=list[Product])
def list_products(session: Session = Depends(get_session)):
    return ProductService.list_products(session)