"""
Common schemas for FastCore v2.

This module provides reusable Pydantic schemas for API responses and metadata.

Limitations:
- Envelope structure is fixed; customization requires subclassing or code changes
- Only basic metadata (timestamp, version, pagination) is included by default
- No built-in support for localization or advanced metadata
- No automatic OpenAPI customization beyond FastAPI defaults
"""

from fastcore.schemas.metadata import BaseMetadata, ResponseMetadata
from fastcore.schemas.response import (
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
