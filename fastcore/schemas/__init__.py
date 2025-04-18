"""
Common schemas for FastCore v2.

This module provides reusable Pydantic schemas for API responses and metadata.
"""

from .metadata import BaseMetadata, ResponseMetadata
from .response import (
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
