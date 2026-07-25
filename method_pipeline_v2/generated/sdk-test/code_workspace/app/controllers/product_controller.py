"""
Product REST controller.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from app.infrastructure.graceful_degradation import GracefulDegradationManager
from app.schemas.product_schema import (
    ProductCreate,
    ProductResponse,
    ProductSearchResponse,
)
from app.services.product_service import ProductService


def create_product_router(
    dep_service: Callable[[], ProductService],
    degradation_mgr: GracefulDegradationManager,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/products", tags=["Products"])

    @router.get("", response_model=ProductSearchResponse)
    async def search_products(
        q: str | None = Query(None, description="Search query"),
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        service: ProductService = Depends(dep_service),
    ):
        if degradation_mgr.state.product_search_disabled:
            raise HTTPException(
                status_code=503,
                detail="Product search is temporarily disabled due to high load. "
                       "Please try again later.",
            )
        products, total = await service.search(query=q, page=page, size=size)
        return ProductSearchResponse(
            products=products,
            total=total,
            page=page,
            size=size,
        )

    @router.get("/{product_id}", response_model=ProductResponse)
    async def get_product(
        product_id: str,
        service: ProductService = Depends(dep_service),
    ):
        product = await service.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @router.post("", response_model=ProductResponse, status_code=201)
    async def create_product(
        body: ProductCreate,
        service: ProductService = Depends(dep_service),
    ):
        return await service.create(
            name=body.name,
            description=body.description,
            base_price=body.base_price,
            currency=body.currency,
            stock_quantity=body.stock_quantity,
        )

    return router
