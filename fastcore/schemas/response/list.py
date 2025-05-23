"""
List response schema for collections of objects.

This module contains schemas used when returning lists/collections
of items from API endpoints.

Limitations:
- Envelope structure is fixed; customization requires subclassing or code changes
- Only basic metadata (timestamp, version, pagination) is included by default
- No built-in support for localization or advanced metadata
"""

from typing import Generic, List, Optional, TypeVar

from pydantic import Field

from fastcore.schemas.metadata import BaseMetadata
from fastcore.schemas.response.base import BaseResponse

T = TypeVar("T")


class ListMetadata(BaseMetadata):
    """
    Metadata specific to list responses.

    Features:
    - Includes total, page, page_size, has_next, has_previous

    Limitations:
    - Only basic metadata (timestamp, version, pagination) is included by default
    - No built-in support for advanced metadata or localization

    Attributes:
        total: Total number of items
        page: Current page number
        page_size: Maximum items per page
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
    """

    total: int = Field(default=0, description="Total number of items")
    page: Optional[int] = Field(default=None, description="Current page number")
    page_size: Optional[int] = Field(default=None, description="Maximum items per page")
    has_next: Optional[bool] = Field(
        default=None, description="Whether there are more pages after this one"
    )
    has_previous: Optional[bool] = Field(
        default=None, description="Whether there are pages before this one"
    )


class ListResponse(BaseResponse[List[T], ListMetadata], Generic[T]):
    """
    Schema for list/collection API responses.

    Features:
    - Standardized envelope for list/collection responses
    - Includes list data and pagination metadata

    Limitations:
    - Envelope structure is fixed; customization requires subclassing or code changes
    - Only basic metadata (timestamp, version, pagination) is included by default
    - No built-in support for localization or advanced metadata

    Attributes:
        data: The list of response items
        metadata: Pagination and response metadata
        success: Whether the request was successful
        message: Optional message providing additional context
    """

    data: List[T] = Field(default_factory=list, description="List of items")
    metadata: ListMetadata = Field(
        default_factory=ListMetadata,
        description="Response metadata including pagination info",
    )
