"""
Product routes — /api/v1/products

POST   /              Create product
GET    /              List products (paginated)
GET    /search        Search products by keyword/price (NFR 1.1 core journey)
GET    /{id}          Get product
PUT    /{id}          Update product
DELETE /{id}          Delete product
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from oms.controllers.product import product_controller
from oms.database import get_session
from oms.schemas.product import ProductCreate, ProductUpdate, ProductRead
from oms.schemas.common import PaginatedResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductRead, status_code=201)
async def create_product(data: ProductCreate, session: AsyncSession = Depends(get_session)) -> ProductRead:
    """Create a new product."""
    return await product_controller.create_product(data, session)


@router.get("/", response_model=PaginatedResponse[ProductRead])
async def list_products(page: int = 1, page_size: int = 20, session: AsyncSession = Depends(get_session)) -> PaginatedResponse[ProductRead]:
    """List all products with pagination."""
    return await product_controller.list_products(session, page=page, page_size=page_size)


@router.get("/search", response_model=PaginatedResponse[ProductRead])
async def search_products(
    q: str | None = Query(default=None, description="Description keyword"),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    currency: str | None = Query(default=None, max_length=3),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[ProductRead]:
    """
    Search products by description keyword and/or price range.
    This is a core journey endpoint optimised for low latency (NFR 1.1).
    """
    return await product_controller.search_products(
        session, q=q, min_price=min_price, max_price=max_price,
        currency=currency, page=page, page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: str, session: AsyncSession = Depends(get_session)) -> ProductRead:
    """Get a product by ID."""
    return await product_controller.get_product(product_id, session)


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(product_id: str, data: ProductUpdate, session: AsyncSession = Depends(get_session)) -> ProductRead:
    """Update a product's fields."""
    return await product_controller.update_product(product_id, data, session)


@router.delete("/{product_id}")
async def delete_product(product_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    """Delete a product."""
    return await product_controller.delete_product(product_id, session)