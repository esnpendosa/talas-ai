"""
TALAS AI — Common Schemas
Schema Pydantic yang digunakan di berbagai tempat.
"""
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Response standar API."""
    success: bool = True
    message: str = "OK"


class DataResponse(BaseResponse, Generic[T]):
    """Response dengan data."""
    data: Optional[T] = None


class PaginatedResponse(BaseResponse, Generic[T]):
    """Response dengan pagination."""
    data: List[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class ErrorResponse(BaseModel):
    """Response error standar."""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    # Jangan tampilkan stack trace ke user


class HealthCheck(BaseModel):
    """Response health check."""
    status: str
    app_name: str
    version: str
    environment: str
    database: dict
    timestamp: str
