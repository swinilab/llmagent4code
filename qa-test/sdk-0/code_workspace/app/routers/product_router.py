"""
Product router exposing product endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

from app.cache.response_cache import get_or_set_cached_product_list

router = APIRouter()

@router.get("/products", response_model=List[dict], status_code=status.HTTP_200_OK)
async def list_products():
    try:
        return await get_or_set_cached_product_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
