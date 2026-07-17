"""
Product REST API controller.
Handles HTTP requests for product operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms.config.database import get_db
from oms.models.product import ProductCreate, ProductUpdate, ProductResponse
from oms.services.product_service import ProductService

product_router = APIRouter(prefix="/api/v1/products", tags=["products"])


@product_router.get("", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None, min_length=1),
    db: AsyncSession = Depends(get_db)
):
    """Get all products with optional search."""
    service = ProductService(db)
    if search:
        return await service.search_products(query=search, skip=skip, limit=limit)
    return await service.get_all_products(skip=skip, limit=limit)


@product_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Get a product by ID."""
    service = ProductService(db)
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@product_router.post("", response_model=ProductResponse, status_code=201)
async def create_product(product_data: ProductCreate, db: AsyncSession = Depends(get_db)):
    """Create a new product."""
    service = ProductService(db)
    return await service.create_product(product_data)


@product_router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product_data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing product."""
    service = ProductService(db)
    product = await service.update_product(product_id, product_data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@product_router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a product."""
    service = ProductService(db)
    deleted = await service.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return None


@product_router.get("/count")
async def get_product_count(db: AsyncSession = Depends(get_db)):
    """Get total number of products."""
    service = ProductService(db)
    return {"count": await service.get_product_count()}
