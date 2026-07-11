"""
Product API endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.models import Product
from app.domain.schemas import ProductCreate, ProductResponse
from app.infrastructure.database import get_db_session
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Product:
    service = ProductService(session)
    return await service.create_product(data)


@router.get("", response_model=list[ProductResponse])
async def list_products(
    session: AsyncSession = Depends(get_db_session),
) -> list[Product]:
    service = ProductService(session)
    return await service.list_available_products()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Product:
    service = ProductService(session)
    product = await service.get_product(product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    return product
