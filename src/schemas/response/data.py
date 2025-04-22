"""
Data response schema for single-object responses.

This module contains the schema used when returning a single item
from an API endpoint.
"""

from typing import Generic, TypeVar

from pydantic import Field

from src.schemas.metadata import ResponseMetadata
from src.schemas.response.base import BaseResponse

T = TypeVar("T")


class DataResponse(BaseResponse[T, ResponseMetadata], Generic[T]):
    """
    Schema for single-object API responses.

    Example:
        Response for getting a single user:
        {
            "success": true,
            "data": {"id": 1, "name": "John"},
            "metadata": {
                "timestamp": "2025-04-15T10:30:00",
                "version": "1.0"
            },
            "message": "User retrieved successfully"
        }
    """

    data: T = Field(..., description="Response payload (required)")  # required
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata, description="Standard response metadata"
    )
