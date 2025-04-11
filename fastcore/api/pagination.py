"""
Pagination utilities for FastAPI applications.

This module provides standardized pagination functionality for API endpoints,
including request parameters, response models, and database query helpers.
"""

from math import ceil
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union

from fastapi import Query
from pydantic import BaseModel, ConfigDict, create_model

from fastcore.api.responses import (
    BaseResponse,
    FilterInfo,
    ListMetadata,
    ListResponse,
    SortInfo,
)

T = TypeVar("T")


class PaginationParams:
    """
    Query parameters for pagination.

    This class is designed to be used as a dependency in FastAPI route functions
    to provide standardized pagination parameters.

    Attributes:
        page: Page number (1-indexed)
        size: Number of items per page
        offset: Optional offset to override page-based pagination
        limit: Optional limit to override size-based pagination

    Example:
        ```python
        @app.get("/items/")
        def get_items(pagination: PaginationParams = Depends()):
            skip = pagination.get_skip()
            limit = pagination.size
            items = db.query(Item).offset(skip).limit(limit).all()
            return items
        ```
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        size: int = Query(20, ge=1, le=100, description="Number of items per page"),
        offset: Optional[int] = Query(
            None, ge=0, description="Optional offset override"
        ),
        limit: Optional[int] = Query(
            None, ge=1, le=100, description="Optional limit override"
        ),
    ):
        """
        Initialize pagination parameters.

        Args:
            page: Page number (1-indexed)
            size: Number of items per page
            offset: Optional offset to override page-based pagination
            limit: Optional limit to override size-based pagination
        """
        # Handle both raw values and Query objects
        self.page = page.default if hasattr(page, "default") else page
        self.size = size.default if hasattr(size, "default") else size
        self.offset = offset.default if hasattr(offset, "default") else offset
        self.limit = limit.default if hasattr(limit, "default") else limit

    def get_skip(self) -> int:
        """
        Calculate the number of items to skip.

        Returns:
            Number of items to skip for the current page
        """
        if self.offset is not None:
            return self.offset
        return (self.page - 1) * self.size

    def get_limit(self) -> int:
        """
        Get the number of items per page.

        Returns:
            Number of items per page
        """
        return self.limit if self.limit is not None else self.size

    def to_dict(self) -> Dict[str, int]:
        """
        Convert pagination parameters to a dictionary.

        Returns:
            Dictionary with pagination parameters
        """
        result = {"page": self.page, "size": self.size}
        if self.offset is not None:
            result["offset"] = self.offset
        if self.limit is not None:
            result["limit"] = self.limit
        return result

    def to_metadata(
        self,
        total_items: int,
        filtered_count: Optional[int] = None,
    ) -> ListMetadata:
        """
        Convert pagination parameters to ListMetadata.

        Args:
            total_items: Total number of items across all pages
            filtered_count: Number of items after filtering

        Returns:
            ListMetadata instance with pagination information
        """
        # Use filtered count for pagination calculations if provided
        count = filtered_count if filtered_count is not None else total_items
        total_pages = ceil(count / self.size) if count > 0 else 0

        return ListMetadata(
            total_count=total_items,
            filtered_count=filtered_count or total_items,
            offset=self.get_skip(),
            limit=self.get_limit(),
            page=self.page,
            page_size=self.size,
            total_pages=total_pages,
            has_next=self.page < total_pages,
            has_previous=self.page > 1,
        )


def paginate(
    items: List[Any],
    params: PaginationParams,
    total_items: int,
    filtered_count: Optional[int] = None,
    applied_filters: Optional[List[Any]] = None,
    applied_sorting: Optional[List[Any]] = None,
    aggregations: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
) -> ListResponse:
    """
    Create a paginated response with metadata.

    Args:
        items: List of items for the current page
        params: Pagination parameters
        total_items: Total number of items (before filtering)
        filtered_count: Number of items after filtering
        applied_filters: List of applied filters
        applied_sorting: List of applied sorts
        aggregations: Optional aggregation results
        message: Optional response message

    Returns:
        ListResponse containing the items and metadata
    """
    # Convert filter conditions to FilterInfo
    filter_info: List[FilterInfo] = []
    if applied_filters:
        for f in applied_filters:
            if isinstance(f, dict):
                filter_info.append(FilterInfo(**f))
            elif hasattr(f, "to_dict"):
                filter_info.append(FilterInfo(**f.to_dict()))
            else:
                filter_info.append(f)

    # Convert sort fields to SortInfo
    sort_info: List[SortInfo] = []
    if applied_sorting:
        for s in applied_sorting:
            if isinstance(s, dict):
                sort_info.append(SortInfo(**s))
            elif hasattr(s, "to_dict"):
                sort_info.append(SortInfo(**s.to_dict()))
            else:
                sort_info.append(s)

    metadata = params.to_metadata(
        total_items=total_items, filtered_count=filtered_count or total_items
    )

    return ListResponse(
        success=True,
        data=items,
        message=message or "Items retrieved successfully",
        list_metadata=metadata,
        applied_filters=filter_info,
        applied_sorting=sort_info,
        aggregations=aggregations,
    )


# Backward compatibility
Page = ListResponse
PageInfo = ListMetadata
