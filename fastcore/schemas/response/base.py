"""
Base response schemas.

This module provides the base response schema that all other response
schemas will inherit from.
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

from fastcore.schemas.metadata import BaseMetadata

T = TypeVar("T")
M = TypeVar("M", bound=BaseMetadata)


class BaseResponse(BaseModel, Generic[T, M]):
    """
    Base schema for all API responses.

    Attributes:
        success: Whether the request was successful
        data: The response payload of type T
        metadata: Response metadata of type M
        message: Optional message providing additional context
    """

    success: bool = Field(
        default=True, description="Indicates if the request was successful"
    )
    data: Optional[T] = Field(default=None, description="Response payload")
    metadata: M
    message: Optional[str] = Field(
        default=None, description="Additional context about the response"
    )
