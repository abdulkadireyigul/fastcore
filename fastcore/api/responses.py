"""
Standardized API response models.

This module provides consistent response structures for all API endpoints
to ensure a unified API interface across applications.
"""

from datetime import UTC, datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseMetadata(BaseModel):
    """Metadata included in all API responses."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0"
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class BaseResponse(BaseModel, Generic[T]):
    """
    Base response model for all API responses.

    This model ensures a consistent response structure across all endpoints.

    Attributes:
        success: Whether the request was successful
        data: The response data
        metadata: Response metadata including timestamp and version
        message: Optional message about the response
        errors: List of errors if any occurred
    """

    model_config = ConfigDict(populate_by_name=True)

    success: bool = True
    data: Optional[T] = None
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    message: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None


class ListMetadata(BaseModel):
    """Additional metadata specific to list responses."""

    total_count: int = 0
    filtered_count: Optional[int] = None
    offset: Optional[int] = None
    limit: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    total_pages: Optional[int] = None
    has_next: Optional[bool] = None
    has_previous: Optional[bool] = None


class FilterInfo(BaseModel):
    """Information about applied filters."""

    field: str
    operator: str
    value: Any


class SortInfo(BaseModel):
    """Information about applied sorting."""

    field: str
    direction: str = "asc"


class ListResponse(BaseResponse[List[T]], Generic[T]):
    """
    Response model for endpoints returning lists of items.

    This model extends BaseResponse to include list-specific metadata
    such as pagination information, applied filters, and sorting details.

    Attributes:
        data: List of items
        list_metadata: Additional list-specific metadata
        applied_filters: List of filters that were applied to the data
        applied_sorting: List of sort criteria that were applied
        aggregations: Optional aggregations or facets for the list
    """

    data: List[T]
    list_metadata: ListMetadata = Field(default_factory=ListMetadata)
    applied_filters: Optional[List[FilterInfo]] = None
    applied_sorting: Optional[List[SortInfo]] = None
    aggregations: Optional[Dict[str, Any]] = None


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseResponse[None]):
    """Response model for error cases."""

    success: bool = False
    errors: List[ErrorDetail]


def create_response(
    data: Optional[Any] = None,
    message: Optional[str] = None,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    errors: Optional[List[Dict[str, Any]]] = None,
    list_metadata: Optional[Dict[str, Any]] = None,
    applied_filters: Optional[List[Dict[str, Any]]] = None,
    applied_sorting: Optional[List[Dict[str, Any]]] = None,
    aggregations: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """
    Create a standardized JSON response.

    Args:
        data: Response data
        message: Optional response message
        success: Whether the request was successful
        metadata: Additional metadata to include
        status_code: HTTP status code
        errors: List of errors if any occurred
        list_metadata: Additional metadata for list responses
        applied_filters: List of filters applied to the data
        applied_sorting: List of sort criteria applied to the data
        aggregations: Optional aggregations or facets for list responses

    Returns:
        Standardized JSON response
    """
    response_data = {
        "success": success,
        "data": data,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0",
            **(metadata or {}),
        },
        "message": message,
        "errors": errors,
    }

    # Add list-specific metadata if this is a list response
    if isinstance(data, list):
        list_metadata = list_metadata or {}
        if "total_count" not in list_metadata:
            list_metadata["total_count"] = len(data)

        response_data["list_metadata"] = list_metadata
        if applied_filters:
            response_data["applied_filters"] = applied_filters
        if applied_sorting:
            response_data["applied_sorting"] = applied_sorting
        if aggregations:
            response_data["aggregations"] = aggregations

    return JSONResponse(
        content=response_data,
        status_code=status_code,
    )
