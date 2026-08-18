"""
API response models
"""
from typing import Optional, Any, Dict, List
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Error response model"""
    message: str
    status_code: int
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Success response model"""
    message: str
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Any]
    total: int
    page: int
    page_size: int
