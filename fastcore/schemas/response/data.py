"""
Data response schema for single-object responses.

This module contains the schema used when returning a single item
from an API endpoint.

Limitations:
- Envelope structure is fixed; customization requires subclassing or code changes
- Only basic metadata (timestamp, version) is included by default
- No built-in support for localization or advanced metadata
"""

from typing import Generic, TypeVar

from pydantic import Field

from fastcore.schemas.metadata import ResponseMetadata
from fastcore.schemas.response.base import BaseResponse

T = TypeVar("T")


class DataResponse(BaseResponse[T, ResponseMetadata], Generic[T]):
    """
    Schema for single-object API responses.

    Features:
    - Standardized envelope for single-object responses
    - Includes required data and standard metadata

    Limitations:
    - Envelope structure is fixed; customization requires subclassing or code changes
    - Only basic metadata (timestamp, version) is included by default
    - No built-in support for localization or advanced metadata

    Attributes:
        data: The response payload (required)
        metadata: Standard response metadata
        success: Whether the request was successful
        message: Optional message providing additional context
    """

    data: T = Field(..., description="Response payload (required)")  # required
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata, description="Standard response metadata"
    )
