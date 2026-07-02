"""
Product controller for handling product-related HTTP requests.

Provides REST API endpoints for product management and search.
"""
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from oms.config.database import get_db_session
from oms.models.schemas import (
    ProductCreate,
    ProductResponse,
    ErrorResponse,
    PaginatedResponse,
)
from oms.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_service(session=Depends(get_db_session)) -> ProductService:
    """Dependency injection for ProductService."""
    return ProductService(session)


@router.post(
    "",
    response_model=ProductResponse,
    summary="Create a new product",
    description="Create a new product with the provided details.",
)
async def create_product(
    product_data: ProductCreate,
    service: ProductService = Depends(get_service),
) -> ProductResponse:
    """
    Create a new product.
    
    Args:
        product_data: Product creation data
        service: Product service instance
        
    Returns:
        Created product response
    """
    return await service.create_product(product_data)


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="Get all products",
    description="Retrieve all products with pagination support.",
)
async def get_all_products(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: ProductService = Depends(get_service),
) -> PaginatedResponse:
    """
    Get all products with pagination.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Product service instance
        
    Returns:
        Paginated list of products
    """
    products = await service.get_all_products(limit=limit, offset=offset)
    total = await service.repository.count()
    return PaginatedResponse(
        items=products,
        total=total,
        page=(offset // limit) + 1 if limit > 0 else 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if limit > 0 else 1,
    )


@router.get(
    "/available",
    response_model=List[ProductResponse],
    summary="Get available products",
    description="Retrieve all available products (in stock).",
)
async def get_available_products(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: ProductService = Depends(get_service),
) -> List[ProductResponse]:
    """
    Get all available products.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Product service instance
        
    Returns:
        List of available products
    """
    return await service.get_available_products(limit=limit, offset=offset)


@router.get(
    "/search",
    response_model=List[ProductResponse],
    summary="Search products",
    description="Search products by name pattern.",
)
async def search_products(
    q: str = Query(..., min_length=1, description="Name pattern to search"),
    service: ProductService = Depends(get_service),
) -> List[ProductResponse]:
    """
    Search products by name.
    
    Args:
        q: Name pattern to search for
        service: Product service instance
        
    Returns:
        List of matching products
    """
    return await service.search_products(q)


@router.get(
    "/price-range",
    response_model=List[ProductResponse],
    summary="Get products by price range",
    description="Retrieve products within a price range.",
)
async def get_products_by_price_range(
    min_price: Decimal = Query(..., ge=0, description="Minimum price"),
    max_price: Decimal = Query(..., ge=0, description="Maximum price"),
    service: ProductService = Depends(get_service),
) -> List[ProductResponse]:
    """
    Get products within a price range.
    
    Args:
        min_price: Minimum price
        max_price: Maximum price
        service: Product service instance
        
    Returns:
        List of products within the price range
    """
    return await service.get_products_by_price_range(min_price, max_price)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get product by ID",
    description="Retrieve a specific product by its ID.",
)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_service),
) -> ProductResponse:
    """
    Get product by ID.
    
    Args:
        product_id: Product ID
        service: Product service instance
        
    Returns:
        Product response
        
    Raises:
        HTTPException: If product not found
    """
    product = await service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Update product",
    description="Update an existing product's details.",
)
async def update_product(
    product_id: int,
    product_data: ProductCreate,
    service: ProductService = Depends(get_service),
) -> ProductResponse:
    """
    Update an existing product.
    
    Args:
        product_id: Product ID
        product_data: Updated product data
        service: Product service instance
        
    Returns:
        Updated product response
        
    Raises:
        HTTPException: If product not found
    """
    product = await service.update_product(product_id, product_data)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.patch(
    "/{product_id}/stock",
    response_model=ProductResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Update product stock",
    description="Update product stock quantity.",
)
async def update_product_stock(
    product_id: int,
    quantity_change: int = Query(..., description="Stock quantity change"),
    service: ProductService = Depends(get_service),
) -> ProductResponse:
    """
    Update product stock quantity.
    
    Args:
        product_id: Product ID
        quantity_change: Amount to add (positive) or remove (negative)
        service: Product service instance
        
    Returns:
        Updated product response
        
    Raises:
        HTTPException: If product not found
    """
    product = await service.update_stock(product_id, quantity_change)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.delete(
    "/{product_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
    summary="Delete product",
    description="Delete a product.",
)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_service),
) -> dict:
    """
    Delete a product.
    
    Args:
        product_id: Product ID
        service: Product service instance
        
    Returns:
        Deletion confirmation
        
    Raises:
        HTTPException: If product not found
    """
    success = await service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return {"message": f"Product {product_id} deleted successfully"}


@router.get(
    "/{product_id}/availability",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
    summary="Check product availability",
    description="Check if product has sufficient stock for a given quantity.",
)
async def check_product_availability(
    product_id: int,
    quantity: int = Query(..., ge=1, description="Required quantity"),
    service: ProductService = Depends(get_service),
) -> dict:
    """
    Check product availability.
    
    Args:
        product_id: Product ID
        quantity: Required quantity
        service: Product service instance
        
    Returns:
        Availability status
        
    Raises:
        HTTPException: If product not found
    """
    available = await service.check_availability(product_id, quantity)
    return {"product_id": product_id, "quantity": quantity, "available": available}
