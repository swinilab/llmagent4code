"""Product REST controller — v1 API (independent entity, not nested under customers)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.models import Product
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/v1/products", tags=["Products"])


@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(body: Product, db: AsyncSession = Depends(get_db)):
    svc = CustomerService(db)
    return await svc.create_product(body)


@router.get("", response_model=list[Product])
async def list_products(db: AsyncSession = Depends(get_db)):
    svc = CustomerService(db)
    return await svc.list_products()


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    svc = CustomerService(db)
    product = await svc.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product