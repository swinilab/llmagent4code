"""
Product Controller - REST endpoints for product management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from ..infrastructure.database import get_db
from ..services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


class CreateProductRequest(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    base_price: float = Field(..., gt=0)
    currency: str = "USD"
    stock_quantity: int = Field(default=0, ge=0)


class UpdateProductRequest(BaseModel):
    description: Optional[str] = None
    base_price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    sku: str
    description: str
    base_price: float
    currency: str
    stock_quantity: int
    is_active: bool
    created_at: str
    updated_at: str


def _to_response(product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        description=product.description,
        base_price=product.base_price,
        currency=product.currency,
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat()
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    request: CreateProductRequest,
    db: Session = Depends(get_db)
):
    """Create a new product."""
    service = ProductService(db)
    
    try:
        product = service.create_product(
            sku=request.sku,
            description=request.description,
            base_price=request.base_price,
            currency=request.currency,
            stock_quantity=request.stock_quantity
        )
        return _to_response(product)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Get product by ID."""
    service = ProductService(db)
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_response(product)


@router.get("/by-sku/{sku}", response_model=ProductResponse)
def get_product_by_sku(
    sku: str,
    db: Session = Depends(get_db)
):
    """Get product by SKU."""
    service = ProductService(db)
    product = service.get_product_by_sku(sku)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_response(product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    request: UpdateProductRequest,
    db: Session = Depends(get_db)
):
    """Update product fields."""
    service = ProductService(db)
    
    update_data = {}
    if request.description is not None:
        update_data["description"] = request.description
    if request.base_price is not None:
        update_data["base_price"] = request.base_price
    if request.currency is not None:
        update_data["currency"] = request.currency
    if request.stock_quantity is not None:
        update_data["stock_quantity"] = request.stock_quantity
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    
    product = service.update_product(product_id, **update_data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_response(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Deactivate a product (soft delete)."""
    service = ProductService(db)
    product = service.deactivate_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("", response_model=List[ProductResponse])
def list_products(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List products."""
    service = ProductService(db)
    if active_only:
        products = service.list_active_products(skip=skip, limit=limit)
    else:
        products = service.list_products(skip=skip, limit=limit)
    return [_to_response(p) for p in products]


@router.post("/{product_id}/stock", response_model=ProductResponse)
def update_stock(
    product_id: str,
    quantity_change: int,
    db: Session = Depends(get_db)
):
    """Update product stock quantity."""
    service = ProductService(db)
    try:
        product = service.update_stock(product_id, quantity_change)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return _to_response(product)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
