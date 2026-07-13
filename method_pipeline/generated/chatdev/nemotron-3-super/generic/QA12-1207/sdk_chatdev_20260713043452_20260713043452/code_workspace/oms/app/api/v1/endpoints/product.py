from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.services.product import ProductService
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate, ProductInDB
from app.database import get_db

router = APIRouter()

def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    repo = ProductRepository(db)
    return ProductService(repo)

@router.post("/", response_model=ProductInDB, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    return service.create(product_in)

@router.get("/{product_id}", response_model=ProductInDB)
async def read_product(
    product_id: int,
    service: ProductService = Depends(get_product_service)
):
    product = service.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/", response_model=List[ProductInDB])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    service: ProductService = Depends(get_product_service)
):
    return service.get_multi(skip=skip, limit=limit)

@router.put("/{product_id}", response_model=ProductInDB)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    service: ProductService = Depends(get_product_service)
):
    product = service.update(product_id, product_in)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.delete("/{product_id}", response_model=ProductInDB)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service)
):
    product = service.delete(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product