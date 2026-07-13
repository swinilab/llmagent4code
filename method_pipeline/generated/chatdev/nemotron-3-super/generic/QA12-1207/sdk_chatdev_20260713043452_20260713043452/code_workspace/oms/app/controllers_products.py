from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, crud
from app.database import get_db

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: schemas.ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product.
    """
    product = await crud.get_product_by_sku(db, sku=product_in.sku)
    if product:
        raise HTTPException(
            status_code=400,
            detail="Product with this SKU already exists",
        )
    return await crud.create_product(db, product_in=product_in)


@router.get("/", response_model=List[schemas.Product])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve products.
    """
    products = await crud.get_products(db, skip=skip, limit=limit)
    return products


@router.get("/{product_id}", response_model=schemas.Product)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific product by ID.
    """
    product = await crud.get_product(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=schemas.Product)
async def update_product(
    product_id: int,
    product_in: schemas.ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a product.
    """
    product = await crud.update_product(
        db, product_id=product_id, product_in=product_in
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", response_model=schemas.Product)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product.
    """
    product = await crud.delete_product(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product