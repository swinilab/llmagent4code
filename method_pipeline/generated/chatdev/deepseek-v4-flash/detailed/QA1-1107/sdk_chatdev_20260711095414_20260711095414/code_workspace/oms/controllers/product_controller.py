"""
Product controller — browse/search with cache-aside.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from oms.infrastructure.database import get_db
from oms.infrastructure.metrics import http_requests_total
from oms.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


class ProductResponse(BaseModel):
    id: str
    description: str
    base_price: str
    currency: str
    stock_available: int
    last_modified: str


class PriceUpdateRequest(BaseModel):
    new_price: float


class StockUpdateRequest(BaseModel):
    delta: int


@router.get("/search", response_model=list[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    """Product search/browse — p95 ≤ 150 ms target."""
    service = ProductService(db)
    products = await service.search_products(q, limit)
    http_requests_total.labels(method="GET", endpoint="/api/v1/products/search", status="200").inc()
    return [
        ProductResponse(
            id=str(p.id),
            description=p.description,
            base_price=str(p.base_price),
            currency=p.currency,
            stock_available=p.stock_available,
            last_modified=p.last_modified.isoformat(),
        )
        for p in products
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Get single product (cache-aside)."""
    service = ProductService(db)
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    http_requests_total.labels(method="GET", endpoint=f"/api/v1/products/{{id}}", status="200").inc()
    return ProductResponse(
        id=str(product.id),
        description=product.description,
        base_price=str(product.base_price),
        currency=product.currency,
        stock_available=product.stock_available,
        last_modified=product.last_modified.isoformat(),
    )


@router.patch("/{product_id}/price", response_model=ProductResponse)
async def update_price(
    product_id: UUID,
    req: PriceUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update price (invalidates cache)."""
    service = ProductService(db)
    product = await service.update_price(product_id, req.new_price)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(
        id=str(product.id),
        description=product.description,
        base_price=str(product.base_price),
        currency=product.currency,
        stock_available=product.stock_available,
        last_modified=product.last_modified.isoformat(),
    )


@router.patch("/{product_id}/stock", response_model=ProductResponse)
async def update_stock(
    product_id: UUID,
    req: StockUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update stock (invalidates cache)."""
    service = ProductService(db)
    product = await service.update_stock(product_id, req.delta)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(
        id=str(product.id),
        description=product.description,
        base_price=str(product.base_price),
        currency=product.currency,
        stock_available=product.stock_available,
        last_modified=product.last_modified.isoformat(),
    )
