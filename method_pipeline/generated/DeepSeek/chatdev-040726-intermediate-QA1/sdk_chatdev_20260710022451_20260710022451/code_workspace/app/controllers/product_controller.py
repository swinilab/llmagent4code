"""
Product REST controller — search/browse is a hot path (NFR 1.1, p95 ≤ 150 ms).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas import (
    PaginatedResponse,
    ProductCreate,
    ProductResponse,
    ProductSearchParams,
)
from app.infrastructure.database import get_db
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db),
):
    svc = ProductService(session)
    product = await svc.create_product(data)
    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_db),
):
    svc = ProductService(session)
    return await svc.get_product(product_id)


@router.get("", response_model=PaginatedResponse)
async def search_products(
    q: Optional[str] = Query(None, description="Search query"),
    min_price: Optional[Decimal] = Query(None, ge=0),
    max_price: Optional[Decimal] = Query(None, ge=0),
    in_stock_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    svc = ProductService(session)
    params = ProductSearchParams(
        q=q,
        min_price=min_price,
        max_price=max_price,
        in_stock_only=in_stock_only,
        page=page,
        page_size=page_size,
    )
    items, total = await svc.search_products(params)
    return PaginatedResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductCreate,
    session: AsyncSession = Depends(get_db),
):
    svc = ProductService(session)
    return await svc.update_product(product_id, data)
