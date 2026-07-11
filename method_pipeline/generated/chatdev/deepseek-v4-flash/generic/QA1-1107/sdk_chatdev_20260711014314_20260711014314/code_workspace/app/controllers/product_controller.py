"""
REST controller for Product entity.
Provides CRUD + search endpoints under /api/v1/products.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    """Create a new product."""
    product = await ProductService.create(db, data)
    return product


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a product by ID."""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/", response_model=List[ProductRead])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: str = Query(None, min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """List products with optional search and pagination."""
    if search:
        products = await ProductService.search(db, search, skip=skip, limit=limit)
    else:
        products = await ProductService.get_all(db, skip=skip, limit=limit)
    return products


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: str, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    """Update a product."""
    product = await ProductService.update(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a product by ID."""
    deleted = await ProductService.delete(db, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
