"""
Product REST API controller
Implements validation and request/response mapping
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms_backend.repository.base import get_db
from oms_backend.service.product_service import ProductService
from oms_backend.domain.schemas import ProductCreate, ProductResponse
from oms_backend.domain.models import Product

product_router = APIRouter(prefix="/api/v1/products", tags=["products"])


def product_to_response(product: Product) -> ProductResponse:
    """Convert Product model to response schema"""
    return ProductResponse(
        id=product.id,
        description=product.description,
        price={
            "amount": float(product.price_amount),
            "currency": product.price_currency
        },
        createdAt=product.created_at,
        updatedAt=product.updated_at
    )


@product_router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db)
) -> ProductResponse:
    """Create a new product"""
    service = ProductService(session)
    try:
        product = await service.create_product(data)
        return product_to_response(product)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@product_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_db)
) -> ProductResponse:
    """Get product by ID"""
    import uuid
    try:
        uuid.UUID(product_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = ProductService(session)
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_to_response(product)


@product_router.get("", response_model=List[ProductResponse])
async def get_all_products(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
) -> List[ProductResponse]:
    """Get all products with pagination"""
    service = ProductService(session)
    products = await service.get_all_products(limit, offset)
    return [product_to_response(p) for p in products]
