"""
ProductController — REST endpoints for product catalog.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.db.connection import get_session
from oms_backend.schemas.domain import Product, ProductCreate, ProductUpdate, ProductSearchResult, paginate
from oms_backend.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Create a new product."""
    svc = ProductService(session)
    return await svc.create(data)


@router.get("/search", response_model=dict)
async def search_products(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Full-text search for products.
    Uses PostgreSQL GIN index for NFR 1.1 (low-latency search).
    """
    svc = ProductService(session)
    products, total = await svc.search(query=q, page=page, page_size=page_size)
    return paginate(
        [ProductSearchResult.model_validate(p) for p in products],
        total=total, page=page, page_size=page_size
    ).model_dump()


@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get a product by ID."""
    svc = ProductService(session)
    product = await svc.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("", response_model=dict)
async def list_products(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all active products (paginated)."""
    svc = ProductService(session)
    products, total = await svc.list_active(page=page, page_size=page_size)
    return paginate(
        [Product.model_validate(p) for p in products],
        total=total, page=page, page_size=page_size
    ).model_dump()


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Update a product."""
    svc = ProductService(session)
    updated = await svc.update(product_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated
