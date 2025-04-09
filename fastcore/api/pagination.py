"""
Pagination utilities for FastAPI applications.

This module provides standardized pagination functionality for API endpoints,
including request parameters, response models, and database query helpers.
"""

from math import ceil
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union

from fastapi import Query
from pydantic import BaseModel, ConfigDict, create_model

T = TypeVar("T")


class PaginationParams:
    """
    Query parameters for pagination.

    This class is designed to be used as a dependency in FastAPI route functions
    to provide standardized pagination parameters.

    Attributes:
        page: Page number (1-indexed)
        size: Number of items per page

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
    ):
        """
        Initialize pagination parameters.

        Args:
            page: Page number (1-indexed)
            size: Number of items per page
        """
        # Handle both raw values and Query objects
        self.page = page.default if hasattr(page, "default") else page
        self.size = size.default if hasattr(size, "default") else size

    def get_skip(self) -> int:
        """
        Calculate the number of items to skip.

        Returns:
            Number of items to skip for the current page
        """
        return (self.page - 1) * self.size

    def get_limit(self) -> int:
        """
        Get the number of items per page.

        Returns:
            Number of items per page
        """
        return self.size

    def to_dict(self) -> Dict[str, int]:
        """
        Convert pagination parameters to a dictionary.

        Returns:
            Dictionary with page and size keys
        """
        return {"page": self.page, "size": self.size}


class PageInfo(BaseModel):
    """
    Pagination metadata for paginated responses.

    This class provides information about the current page, total pages,
    and total items in a paginated response.

    Attributes:
        page: Current page number
        size: Number of items per page
        total_pages: Total number of pages
        total_items: Total number of items
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
    """

    model_config = ConfigDict(populate_by_name=True)

    page: int
    size: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool

    @classmethod
    def from_parameters(cls, params: PaginationParams, total_items: int) -> "PageInfo":
        """
        Create page info from pagination parameters and total item count.

        Args:
            params: Pagination parameters
            total_items: Total number of items

        Returns:
            PageInfo instance
        """
        total_pages = ceil(total_items / params.size) if total_items > 0 else 0

        return cls(
            page=params.page,
            size=params.size,
            total_pages=total_pages,
            total_items=total_items,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )


class Page(BaseModel, Generic[T]):
    """
    Paginated response containing items and pagination metadata.

    This generic model wraps a list of items with pagination information.

    Attributes:
        items: List of items on the current page
        page_info: Pagination metadata

    Example:
        ```python
        @app.get("/items/", response_model=Page[Item])
        def get_items(pagination: PaginationParams = Depends()):
            skip = pagination.get_skip()
            limit = pagination.size

            # Get items for the current page
            items = db.query(Item).offset(skip).limit(limit).all()

            # Get total count for pagination metadata
            total = db.query(Item).count()

            # Create paginated response
            return paginate(items, pagination, total)
        ```
    """

    model_config = ConfigDict(populate_by_name=True)

    items: List[T]
    page_info: PageInfo


def paginate(items: Sequence[T], params: PaginationParams, total_items: int) -> Page[T]:
    """
    Create a paginated response from a sequence of items.

    Args:
        items: Sequence of items for the current page
        params: Pagination parameters
        total_items: Total number of items across all pages

    Returns:
        Page object containing items and pagination metadata

    Example:
        ```python
        @app.get("/items/")
        def get_items(pagination: PaginationParams = Depends()):
            # Get items for the current page
            items = db.query(Item).offset(pagination.get_skip()).limit(pagination.size).all()

            # Get total count
            total = db.query(Item).count()

            # Return paginated response
            return paginate(items, pagination, total)
        ```
    """
    page_info = PageInfo.from_parameters(params, total_items)
    return Page[Any](items=list(items), page_info=page_info)


def get_paginated_response_model(item_model: Type[BaseModel]) -> Type[BaseModel]:
    """
    Create a typed paginated response model for a specific item type.

    This function creates a Pydantic model that represents a paginated response
    for a specific item type, which can be used as a response_model in FastAPI routes.

    Args:
        item_model: Pydantic model for the items in the response

    Returns:
        Pydantic model for a paginated response of the specified item type

    Example:
        ```python
        class ItemResponse(BaseModel):
            id: int
            name: str

        # Create a paginated response model for ItemResponse
        PaginatedItems = get_paginated_response_model(ItemResponse)

        @app.get("/items/", response_model=PaginatedItems)
        def get_items(pagination: PaginationParams = Depends()):
            # Function implementation
            pass
        ```
    """
    model = create_model(
        f"Page{item_model.__name__}",
        items=(List[item_model], ...),
        page_info=(PageInfo, ...),
        __base__=Page,  # Use Page class directly as base
    )

    # Add model_fields property for compatibility with both Pydantic v1 and v2
    if not hasattr(model, "model_fields"):
        model.model_fields = getattr(model, "__fields__", {})

    return model
