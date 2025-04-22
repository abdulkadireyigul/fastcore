"""
Common schemas for FastCore v2.

This module provides reusable Pydantic schemas for API responses and metadata.
"""

from src.schemas.metadata import BaseMetadata, ResponseMetadata
from src.schemas.response import (
    BaseResponse,
    DataResponse,
    ErrorInfo,
    ErrorResponse,
    ListMetadata,
    ListResponse,
    TokenResponse,
)

__all__ = [
    # Metadata schemas
    "BaseMetadata",
    "ResponseMetadata",
    # Response schemas
    "BaseResponse",
    "DataResponse",
    "ErrorResponse",
    "ErrorInfo",
    "ListResponse",
    "ListMetadata",
    "TokenResponse",
]
