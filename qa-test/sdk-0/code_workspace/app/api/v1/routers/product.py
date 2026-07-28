"""Product router – read‑only endpoints used by all roles.

Caching of the product list satisfies **NFR 1.1 Response Time**.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.api.v1.dtos.product_dto import ProductResponseDTO
from app.services.product_service import ProductService
from app.degradation.degradation_manager import DegradationManager

router = APIRouter()

product_service = ProductService()

@router.get("/products", response_model=List[ProductResponseDTO], tags=["product"])
async def list_products(role: str = Depends()):
    # Graceful degradation – if system is degraded, we still serve product catalog
    # but with a cached response and possible reduced fields.
    if DegradationManager.is_degraded():
        # In degraded mode we still return cached data (fast path).
        return await product_service.get_cached_products()
    return await product_service.get_all_products()
