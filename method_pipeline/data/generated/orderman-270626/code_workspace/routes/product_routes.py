"""
Product Routes - API endpoints for Product operations.
Defines RESTful endpoints for product management.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.models import get_session
from controllers.product_controller import ProductController
from shared.models import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductListResponse,
    APIResponse,
)

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    search: Optional[str] = Query(None, description="Search term for name or description"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all products with pagination, optionally filtered by search term.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **search**: Optional search term to filter by name or description
    """
    controller = ProductController(db)
    
    if search:
        return await controller.search_products(search_term=search, skip=skip, limit=limit)
    
    return await controller.get_all_products(skip=skip, limit=limit)


@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific product by ID.
    
    - **product_id**: The unique product identifier
    """
    controller = ProductController(db)
    product = await controller.get_product(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.get("/sku/{sku}", response_model=Product)
async def get_product_by_sku(
    sku: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a product by SKU.
    
    - **sku**: Product stock keeping unit
    """
    controller = ProductController(db)
    product = await controller.get_product_by_sku(sku)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.post("", response_model=Product, status_code=201)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new product.
    
    - **name**: Product name
    - **description**: Product description
    - **price**: Product price (must be > 0)
    - **sku**: Stock keeping unit (must be unique)
    - **stock_quantity**: Available stock quantity (default: 0)
    """
    controller = ProductController(db)
    
    # Check if SKU already exists
    existing = await controller.get_product_by_sku(product_data.sku)
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    return await controller.create_product(product_data)


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_session),
):
    """
    Update an existing product.
    
    - **product_id**: The unique product identifier
    - **name**: Optional new name
    - **description**: Optional new description
    - **price**: Optional new price
    - **sku**: Optional new SKU
    - **stock_quantity**: Optional new stock quantity
    """
    controller = ProductController(db)
    
    product = await controller.update_product(product_id, product_data)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.patch("/{product_id}/stock", response_model=Product)
async def update_product_stock(
    product_id: int,
    quantity_change: int = Query(..., description="Amount to add (positive) or remove (negative)"),
    db: AsyncSession = Depends(get_session),
):
    """
    Update product stock quantity.
    
    - **product_id**: The unique product identifier
    - **quantity_change**: Amount to add (positive) or remove (negative)
    """
    controller = ProductController(db)
    
    product = await controller.update_stock(product_id, quantity_change)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.delete("/{product_id}", response_model=APIResponse)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Delete a product.
    
    - **product_id**: The unique product identifier
    """
    controller = ProductController(db)
    
    success = await controller.delete_product(product_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return APIResponse(success=True, message="Product deleted successfully")
