"""
Product controller with REST endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from decimal import Decimal
from app.db.connection_pool import get_db
from app.services.product_service import ProductService
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v1/products", tags=["products"])


class PriceRequest(BaseModel):
    """Request model for price"""
    amount: Decimal = Field(..., ge=Decimal("0.01"), le=Decimal("999999.99"))
    currency: str = Field(..., min_length=3, max_length=3)


class ProductCreateRequest(BaseModel):
    """Request model for creating a product"""
    description: str = Field(..., min_length=3, max_length=500)
    price: PriceRequest


class ProductResponse(BaseModel):
    """Response model for product"""
    id: str
    description: str
    price: dict


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(request: ProductCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new product"""
    service = ProductService(session)
    try:
        product = await service.create_product(
            description=request.description,
            amount=request.price.amount,
            currency=request.price.currency,
        )
        return ProductResponse(
            id=str(product.id),
            description=product.description,
            price=product.price.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[ProductResponse])
async def list_products(limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_db)):
    """List all products"""
    service = ProductService(session)
    products = await service.get_all_products(limit, offset)
    return [
        ProductResponse(
            id=str(p.id),
            description=p.description,
            price=p.price.model_dump(),
        )
        for p in products
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, session: AsyncSession = Depends(get_db)):
    """Get product by ID"""
    service = ProductService(session)
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse(
        id=str(product.id),
        description=product.description,
        price=product.price.model_dump(),
    )
