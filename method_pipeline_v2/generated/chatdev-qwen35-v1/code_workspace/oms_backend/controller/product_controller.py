"""
Product controller
REST endpoints for product operations
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.infrastructure.database import get_db
from oms_backend.service import ProductService
from oms_backend.domain.models import Product, ProductCreate
from oms_backend.controller.responses import ErrorResponse
from oms_backend.utils.exceptions import OMSException, NotFoundException, ValidationException
from oms_backend.utils.rate_limiter import rate_limiter


router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "",
    response_model=Product,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Create a new product",
    description="Create a new product with the provided details.",
)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new product.
    NFR 1.1: Rate limiting applied.
    """
    if not rate_limiter.is_allowed("create_product"):
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "retry_after_seconds": 60}
        )
    
    service = ProductService(db)
    try:
        return service.create_product(data)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "field": e.field})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.get(
    "",
    response_model=List[Product],
    summary="Get all products",
    description="Retrieve a list of all products.",
)
def get_all_products(db: Session = Depends(get_db)):
    """Get all products."""
    service = ProductService(db)
    return service.get_all_products()


@router.get(
    "/{product_id}",
    response_model=Product,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Product not found"},
    },
    summary="Get product by ID",
    description="Retrieve a product by their unique ID.",
)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get product by ID."""
    try:
        uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = ProductService(db)
    try:
        return service.get_product(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.put(
    "/{product_id}",
    response_model=Product,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID or validation error"},
        404: {"model": ErrorResponse, "description": "Product not found"},
    },
    summary="Update product",
    description="Update an existing product's details.",
)
def update_product(
    product_id: str,
    data: dict,
    db: Session = Depends(get_db),
):
    """Update product by ID."""
    try:
        uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = ProductService(db)
    try:
        return service.update_product(uuid, data)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ValidationException as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "field": e.field})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Product not found"},
    },
    summary="Delete product",
    description="Delete a product by their unique ID.",
)
def delete_product(product_id: str, db: Session = Depends(get_db)):
    """Delete product by ID."""
    try:
        uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = ProductService(db)
    try:
        service.delete_product(uuid)
        return None
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})
