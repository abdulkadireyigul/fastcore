"""
Tests for the pagination module.

This module contains tests for the pagination utilities, including
PaginationParams, PageInfo, and the paginate function.
"""

from math import ceil
from typing import List

import pytest
from fastapi import Depends, FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastcore.api.pagination import PaginationParams, paginate
from fastcore.api.responses import FilterInfo, ListMetadata, ListResponse, SortInfo


class TestPaginationParams:
    """Tests for the PaginationParams class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        params = PaginationParams()
        assert params.page == 1
        assert params.size == 20
        assert params.offset is None
        assert params.limit is None

    def test_custom_values(self):
        """Test that custom values are set correctly."""
        params = PaginationParams(page=2, size=50, offset=10, limit=25)
        assert params.page == 2
        assert params.size == 50
        assert params.offset == 10
        assert params.limit == 25

    def test_skip_calculation_with_page(self):
        """Test the calculation of items to skip using page-based pagination."""
        # Page 1 should skip 0 items
        assert PaginationParams(page=1, size=10).get_skip() == 0

        # Page 2 with size 10 should skip 10 items
        assert PaginationParams(page=2, size=10).get_skip() == 10

        # Page 3 with size 25 should skip 50 items
        assert PaginationParams(page=3, size=25).get_skip() == 50

    def test_skip_calculation_with_offset(self):
        """Test the calculation of items to skip using offset-based pagination."""
        params = PaginationParams(page=2, size=10, offset=15)
        assert params.get_skip() == 15  # Offset should override page-based calculation

    def test_limit_calculation(self):
        """Test the calculation of limit."""
        # Default should use size
        params = PaginationParams(page=1, size=20)
        assert params.get_limit() == 20

        # Explicit limit should override size
        params = PaginationParams(page=1, size=20, limit=10)
        assert params.get_limit() == 10

    def test_to_dict(self):
        """Test conversion to dictionary."""
        # Basic parameters
        params = PaginationParams(page=5, size=42)
        assert params.to_dict() == {"page": 5, "size": 42}

        # With offset/limit
        params = PaginationParams(page=5, size=42, offset=10, limit=20)
        result = params.to_dict()
        assert result == {"page": 5, "size": 42, "offset": 10, "limit": 20}

    def test_to_metadata(self):
        """Test conversion to ListMetadata."""
        params = PaginationParams(page=2, size=10)
        metadata = params.to_metadata(total_items=25)

        assert isinstance(metadata, ListMetadata)
        assert metadata.total_count == 25
        assert metadata.filtered_count == 25
        assert metadata.page == 2
        assert metadata.page_size == 10
        assert metadata.total_pages == 3
        assert metadata.has_next is True
        assert metadata.has_previous is True
        assert metadata.offset == 10
        assert metadata.limit == 10


def test_paginate():
    """Test the paginate function with all features."""
    items = ["a", "b", "c"]
    params = PaginationParams(page=1, size=10)
    filters = [FilterInfo(field="type", operator="equals", value="letter")]
    sorting = [SortInfo(field="value", direction="asc")]
    aggregations = {"count_by_type": {"letter": 3}}

    result = paginate(
        items=items,
        params=params,
        total_items=10,
        filtered_count=3,
        applied_filters=filters,
        applied_sorting=sorting,
        aggregations=aggregations,
        message="Test message",
    )

    assert isinstance(result, ListResponse)
    assert result.success is True
    assert result.data == items
    assert result.message == "Test message"
    assert result.list_metadata.total_count == 10
    assert result.list_metadata.filtered_count == 3
    assert result.applied_filters == filters
    assert result.applied_sorting == sorting
    assert result.aggregations == aggregations


class TestFastAPIIntegration:
    """Tests for FastAPI integration."""

    def test_pagination_dependency(self):
        """Test using PaginationParams as a dependency in FastAPI."""
        app = FastAPI()

        @app.get("/test")
        def read_test(pagination: PaginationParams = Depends()):
            return {
                "page": pagination.page,
                "size": pagination.size,
                "skip": pagination.get_skip(),
                "limit": pagination.get_limit(),
            }

        client = TestClient(app)

        # Test with defaults
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"page": 1, "size": 20, "skip": 0, "limit": 20}

        # Test with custom page/size
        response = client.get("/test?page=3&size=15")
        assert response.status_code == 200
        assert response.json() == {"page": 3, "size": 15, "skip": 30, "limit": 15}

        # Test with offset/limit
        response = client.get("/test?offset=25&limit=50")
        assert response.status_code == 200
        assert response.json() == {"page": 1, "size": 20, "skip": 25, "limit": 50}

        # Test validation errors
        response = client.get("/test?page=0")
        assert response.status_code == 422

        response = client.get("/test?size=0")
        assert response.status_code == 422

        response = client.get("/test?offset=-1")
        assert response.status_code == 422

        response = client.get("/test?limit=0")
        assert response.status_code == 422

    def test_enhanced_list_response(self):
        """Test returning an enhanced list response with all features."""
        app = FastAPI()

        class Item(BaseModel):
            id: int
            name: str
            category: str

        @app.get("/items", response_model=ListResponse[Item])
        def read_items(
            category: str = Query(None),
            sort_by: str = Query(None),
            pagination: PaginationParams = Depends(),
        ):
            # Sample data
            all_items = [
                Item(id=1, name="A", category="cat1"),
                Item(id=2, name="B", category="cat2"),
                Item(id=3, name="C", category="cat1"),
            ]

            # Apply filters
            if category:
                items = [i for i in all_items if i.category == category]
            else:
                items = all_items

            # Apply sorting
            if sort_by:
                items.sort(key=lambda x: getattr(x, sort_by))

            # Get paginated subset
            start = pagination.get_skip()
            end = start + pagination.get_limit()
            page_items = items[start:end]

            return paginate(
                items=page_items,
                params=pagination,
                total_items=len(all_items),
                filtered_count=len(items),
                applied_filters=[
                    FilterInfo(field="category", operator="equals", value=category)
                ]
                if category
                else None,
                applied_sorting=[SortInfo(field=sort_by, direction="asc")]
                if sort_by
                else None,
                aggregations={
                    "categories": {
                        "cat1": len([i for i in items if i.category == "cat1"]),
                        "cat2": len([i for i in items if i.category == "cat2"]),
                    }
                },
                message="Items retrieved successfully",
            )

        client = TestClient(app)

        # Test basic pagination
        response = client.get("/items?page=1&size=2")
        data = response.json()
        assert response.status_code == 200
        assert len(data["data"]) == 2
        assert data["success"] is True
        assert data["message"] == "Items retrieved successfully"
        assert data["list_metadata"]["total_count"] == 3
        assert data["list_metadata"]["page"] == 1
        assert data["list_metadata"]["has_next"] is True

        # Test with filtering
        response = client.get("/items?category=cat1")
        data = response.json()
        assert len(data["data"]) == 2
        assert data["list_metadata"]["filtered_count"] == 2
        assert len(data["applied_filters"]) == 1
        assert data["applied_filters"][0]["field"] == "category"

        # Test with sorting
        response = client.get("/items?sort_by=name")
        data = response.json()
        assert data["data"][0]["name"] == "A"
        assert len(data["applied_sorting"]) == 1
        assert data["applied_sorting"][0]["field"] == "name"

        # Test aggregations
        response = client.get("/items")
        data = response.json()
        assert "categories" in data["aggregations"]
        assert data["aggregations"]["categories"]["cat1"] == 2
        assert data["aggregations"]["categories"]["cat2"] == 1
