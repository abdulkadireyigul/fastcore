"""
API utilities for FastAPI applications.

This module provides standardized components for building RESTful APIs,
including pagination, sorting, filtering utilities, and response models.
"""

from fastcore.api.filtering import FilterCondition, FilterOperator, FilterParams
from fastcore.api.pagination import Page, PageInfo, PaginationParams, paginate
from fastcore.api.responses import (
    BaseResponse,
    ErrorDetail,
    ErrorResponse,
    ListResponse,
    ResponseMetadata,
    create_response,
)
from fastcore.api.sorting import SortDirection, SortField, SortParams

__all__ = [
    # Filtering
    "FilterCondition",
    "FilterOperator",
    "FilterParams",
    # Pagination
    "Page",
    "PageInfo",
    "PaginationParams",
    "paginate",
    # Sorting
    "SortDirection",
    "SortField",
    "SortParams",
    # Response models
    "BaseResponse",
    "ListResponse",
    "ErrorResponse",
    "ErrorDetail",
    "ResponseMetadata",
    "create_response",
]
