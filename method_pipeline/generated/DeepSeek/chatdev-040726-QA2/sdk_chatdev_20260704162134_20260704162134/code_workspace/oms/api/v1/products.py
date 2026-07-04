"""
Product REST endpoints (v1).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oms.domain.models import Product, CreateProductRequest
from oms.service.product_service import ProductService
from oms.api.deps import get_product_service

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(
    request: CreateProductRequest,
    service: ProductService = Depends(get_product_service),
) -> Product:
    """Create a new product."""
    return service.create(request)


@router.get("", response_model=list[Product])
def list_products(
    service: ProductService = Depends(get_product_service),
) -> list[Product]:
    """List all products."""
    return service.list_all()


@router.get("/{product_id}", response_model=Product)
def get_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
) -> Product:
    """Get a product by ID."""
    product = service.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product
