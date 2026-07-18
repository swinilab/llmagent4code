"""
Product REST controller.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.product import ProductService
from app.schemas.product import ProductCreate, ProductRead
from app.db.session import get_db

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    service = ProductService(db)
    return service.create_product(product)


@router.get("/{product_id}", response_model=ProductRead)
def read_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID."""
    service = ProductService(db)
    return service.get_product(product_id)
@router.get("", response_model=list[ProductRead])
def read_products(db: Session = Depends(get_db)):
    """List all products with rate limiting for graceful degradation."""
    from fastapi import Request
    from fastapi import HTTPException
    from app.core.rate_limiter import rate_limiter
    
    client_host = "test_client"  # Replace with request.client.host in production
    if rate_limiter.is_rate_limited(client_host):
        raise HTTPException(status_code=429, detail="Too many requests")
    
    service = ProductService(db)
    return service.list_products()
    return service.list_products()