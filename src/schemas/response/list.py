"""
List response schema for collections of objects.

This module contains schemas used when returning lists/collections
of items from API endpoints.
"""

from typing import Generic, List, Optional, TypeVar

from pydantic import Field

from src.schemas.metadata import BaseMetadata
from src.schemas.response.base import BaseResponse

T = TypeVar("T")


class ListMetadata(BaseMetadata):
    """
    Metadata specific to list responses.

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

    Example:
        Response for getting a list of users:
        {
            "success": true,
            "data": [
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"}
            ],
            "metadata": {
                "timestamp": "2025-04-15T10:30:00",
                "version": "1.0",
                "total": 50,
                "page": 1,
                "page_size": 10,
                "has_next": true,
                "has_previous": false
            },
            "message": "Users retrieved successfully"
        }
    """

    data: List[T] = Field(default_factory=list, description="List of items")
    metadata: ListMetadata = Field(
        default_factory=ListMetadata,
        description="Response metadata including pagination info",
    )
