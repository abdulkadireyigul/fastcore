"""
Base response schemas.

This module provides the base response schema that all other response
schemas will inherit from.

Limitations:
- Envelope structure is fixed; customization requires subclassing or code changes
- Only basic metadata (timestamp, version) is included by default
- No built-in support for localization or advanced metadata
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

from fastcore.schemas.metadata import BaseMetadata

T = TypeVar("T")
M = TypeVar("M", bound=BaseMetadata)


class BaseResponse(BaseModel, Generic[T, M]):
    """
    Base schema for all API responses.

    Features:
    - Standardized envelope with success, data, metadata, and message fields
    - Type-safe and reusable for custom responses

    Limitations:
    - Envelope structure is fixed; customization requires subclassing or code changes
    - Only basic metadata (timestamp, version) is included by default
    - No built-in support for localization or advanced metadata
    """

    success: bool = Field(
        default=True, description="Indicates if the request was successful"
    )
    data: Optional[T] = Field(default=None, description="Response payload")
    metadata: M
    message: Optional[str] = Field(
        default=None, description="Additional context about the response"
    )
