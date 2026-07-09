"""Product REST controller with cache-aside browse/search."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_product_service
from app.domain.models import Product
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    base_price: str
    currency: str
    stock_available: int
    last_modified: str
    created_at: str


class UpdateProductRequest(BaseModel):
    base_price: str | None = None
    stock_available: int | None = None


def _product_to_response(p: Product) -> ProductResponse:
    return ProductResponse(
        id=str(p.id),
        name=p.name,
        description=p.description,
        base_price=str(p.base_price),
        currency=p.currency.value,
        stock_available=p.stock_available,
        last_modified=p.last_modified.isoformat(),
        created_at=p.created_at.isoformat(),
    )


@router.get("/search", response_model=list[ProductResponse])
async def search_products(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    product_service: ProductService = Depends(get_product_service),
) -> Any:
    """Search products by name (cached)."""
    products = await product_service.search_products(q, page, page_size)
    return [_product_to_response(p) for p in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    product_service: ProductService = Depends(get_product_service),
) -> Any:
    """Get product by ID (cached)."""
    product = await product_service.get_product(UUID(product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_response(product)


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    product_service: ProductService = Depends(get_product_service),
) -> Any:
    """List all products."""
    products = await product_service.list_products(skip, limit)
    return [_product_to_response(p) for p in products]


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    body: UpdateProductRequest,
    product_service: ProductService = Depends(get_product_service),
) -> Any:
    """Update product price/stock (invalidates cache)."""
    data = {}
    if body.base_price is not None:
        data["base_price"] = Decimal(body.base_price)
    if body.stock_available is not None:
        data["stock_available"] = body.stock_available

    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    product = await product_service.update_product(UUID(product_id), data)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_response(product)
