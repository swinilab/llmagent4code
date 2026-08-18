"""
Product controller with REST endpoints
Implements NFR 2.1 Exception Detection via validation and error handling
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from oms.infrastructure.database import get_async_session
from oms.service.product_service import ProductService
from oms.domain.models import Product, ProductCreate
from oms.infrastructure.exceptions import NotFoundException
from oms.infrastructure.event.rate_limiter import RateLimiter

router = APIRouter(prefix="/api/v1/products", tags=["products"])

def get_product_service(session: AsyncSession = Depends(get_async_session)) -> ProductService:
    """Get product service instance"""
    return ProductService(session)

@router.get("", response_model=List[Product])
async def list_products(
    service: ProductService = Depends(get_product_service)
):
    """List all products"""
    return await service.get_all()

@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service)
):
    """Get product by ID"""
    return await service.get_by_id(product_id)

@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    """
    Create new product
    NFR 1.1: Rate limited
    """
    # Check rate limit (NFR 1.1)
    rate_limiter = RateLimiter.get_instance()
    if not await rate_limiter.is_allowed("product_create"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return await service.create(product)

@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    product: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    """Update existing product"""
    return await service.update(product_id, product)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    service: ProductService = Depends(get_product_service)
):
    """Delete product"""
    success = await service.delete(product_id)
    if not success:
        raise NotFoundException(f"Product {product_id} not found")

product_router = router
