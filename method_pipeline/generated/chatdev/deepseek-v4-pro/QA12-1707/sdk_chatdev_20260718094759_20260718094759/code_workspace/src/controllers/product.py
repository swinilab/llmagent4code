"""
Product REST controller.

Endpoints:
  POST   /api/v1/products          — create product
  GET    /api/v1/products          — list products
  GET    /api/v1/products/search   — search products
  GET    /api/v1/products/{id}     — get product
  PATCH  /api/v1/products/{id}     — update product
  DELETE /api/v1/products/{id}     — delete product
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from src.services.product import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(payload: ProductCreate, session: AsyncSession = Depends(get_session)):
    """Add a new product to the catalogue."""
    svc = ProductService(session)
    return await svc.create(payload)


@router.get("", response_model=list[ProductResponse])
async def list_products(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all products with pagination."""
    svc = ProductService(session)
    return await svc.list_all(limit=limit, offset=offset)


@router.get("/search", response_model=list[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1, description="Description fragment"),
    session: AsyncSession = Depends(get_session),
):
    """Search products by description."""
    svc = ProductService(session)
    return await svc.search(q)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, session: AsyncSession = Depends(get_session)):
    """Retrieve a product by ID."""
    svc = ProductService(session)
    return await svc.get(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Partially update a product."""
    svc = ProductService(session)
    return await svc.update(product_id, payload)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, session: AsyncSession = Depends(get_session)):
    """Remove a product."""
    svc = ProductService(session)
    await svc.delete(product_id)
