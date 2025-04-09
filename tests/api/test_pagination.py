"""
Tests for the pagination module.

This module contains tests for the pagination utilities, including
PaginationParams, PageInfo, and the paginate function.
"""

import math
from typing import List

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastcore.api.pagination import (
    Page,
    PageInfo,
    PaginationParams,
    get_paginated_response_model,
    paginate,
)


class TestPaginationParams:
    """Tests for the PaginationParams class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        params = PaginationParams()
        assert params.page == 1
        assert params.size == 20

    def test_custom_values(self):
        """Test that custom values are set correctly."""
        params = PaginationParams(page=2, size=50)
        assert params.page == 2
        assert params.size == 50

    def test_skip_calculation(self):
        """Test the calculation of items to skip."""
        # Page 1 should skip 0 items
        assert PaginationParams(page=1, size=10).get_skip() == 0

        # Page 2 with size 10 should skip 10 items
        assert PaginationParams(page=2, size=10).get_skip() == 10

        # Page 3 with size 25 should skip 50 items
        assert PaginationParams(page=3, size=25).get_skip() == 50

    def test_limit(self):
        """Test that get_limit returns the size."""
        params = PaginationParams(page=3, size=30)
        assert params.get_limit() == 30

    def test_to_dict(self):
        """Test conversion to dictionary."""
        params = PaginationParams(page=5, size=42)
        assert params.to_dict() == {"page": 5, "size": 42}


class TestPageInfo:
    """Tests for the PageInfo class."""

    def test_from_parameters_empty(self):
        """Test creation from parameters with empty results."""
        params = PaginationParams(page=1, size=10)
        info = PageInfo.from_parameters(params, 0)

        assert info.page == 1
        assert info.size == 10
        assert info.total_items == 0
        assert info.total_pages == 0
        assert info.has_next is False
        assert info.has_previous is False

    def test_from_parameters_single_page(self):
        """Test creation from parameters with results fitting in one page."""
        params = PaginationParams(page=1, size=10)
        info = PageInfo.from_parameters(params, 5)

        assert info.page == 1
        assert info.size == 10
        assert info.total_items == 5
        assert info.total_pages == 1
        assert info.has_next is False
        assert info.has_previous is False

    def test_from_parameters_first_of_many(self):
        """Test creation from parameters on first page of many."""
        params = PaginationParams(page=1, size=10)
        info = PageInfo.from_parameters(params, 25)

        assert info.page == 1
        assert info.size == 10
        assert info.total_items == 25
        assert info.total_pages == 3  # Ceil of 25/10
        assert info.has_next is True
        assert info.has_previous is False

    def test_from_parameters_middle_page(self):
        """Test creation from parameters on a middle page."""
        params = PaginationParams(page=2, size=10)
        info = PageInfo.from_parameters(params, 25)

        assert info.page == 2
        assert info.size == 10
        assert info.total_items == 25
        assert info.total_pages == 3
        assert info.has_next is True
        assert info.has_previous is True

    def test_from_parameters_last_page(self):
        """Test creation from parameters on the last page."""
        params = PaginationParams(page=3, size=10)
        info = PageInfo.from_parameters(params, 25)

        assert info.page == 3
        assert info.size == 10
        assert info.total_items == 25
        assert info.total_pages == 3
        assert info.has_next is False
        assert info.has_previous is True

    def test_from_parameters_partial_page(self):
        """Test creation from parameters with a partial last page."""
        params = PaginationParams(page=2, size=10)
        info = PageInfo.from_parameters(params, 15)

        assert info.page == 2
        assert info.size == 10
        assert info.total_items == 15
        assert info.total_pages == 2
        assert info.has_next is False
        assert info.has_previous is True


def test_paginate():
    """Test the paginate function."""
    items = ["a", "b", "c"]
    params = PaginationParams(page=1, size=10)
    total_items = 3

    result = paginate(items, params, total_items)

    assert isinstance(result, Page)
    assert result.items == items
    assert result.page_info.page == 1
    assert result.page_info.size == 10
    assert result.page_info.total_items == 3
    assert result.page_info.total_pages == 1
    assert result.page_info.has_next is False
    assert result.page_info.has_previous is False


class TestPaginatedResponseModel:
    """Tests for the get_paginated_response_model function."""

    def test_response_model_creation(self):
        """Test creation of a paginated response model."""

        # Sample item model
        class TestItem(BaseModel):
            id: int
            name: str

        # Create paginated response model
        PaginatedTestItems = get_paginated_response_model(TestItem)

        # Check model name and fields
        assert PaginatedTestItems.__name__ == "PageTestItem"
        assert "items" in PaginatedTestItems.model_fields
        assert "page_info" in PaginatedTestItems.model_fields


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
            }

        client = TestClient(app)

        # Test with defaults
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"page": 1, "size": 20, "skip": 0}

        # Test with custom values
        response = client.get("/test?page=3&size=15")
        assert response.status_code == 200
        assert response.json() == {"page": 3, "size": 15, "skip": 30}

        # Test with validation (size must be >= 1)
        response = client.get("/test?size=0")
        assert response.status_code == 422  # Unprocessable Entity

        # Test with validation (page must be >= 1)
        response = client.get("/test?page=0")
        assert response.status_code == 422  # Unprocessable Entity

    def test_paginated_response(self):
        """Test returning a paginated response from a FastAPI endpoint."""

        # Sample item model
        class ItemModel(BaseModel):
            id: int
            name: str

        # Create paginated response model
        PaginatedItems = get_paginated_response_model(ItemModel)

        # Create FastAPI app
        app = FastAPI()

        @app.get("/items", response_model=PaginatedItems)
        def read_items(pagination: PaginationParams = Depends()):
            items = [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"},
                {"id": 4, "name": "Item 4"},
                {"id": 5, "name": "Item 5"},
            ]

            # Apply pagination
            start = pagination.get_skip()
            end = start + pagination.size
            page_items = items[start:end]

            # Return paginated response
            return paginate(page_items, pagination, len(items))

        client = TestClient(app)

        # Test first page
        response = client.get("/items?page=1&size=2")
        data = response.json()

        assert response.status_code == 200
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == 1
        assert data["items"][1]["id"] == 2
        assert data["page_info"]["page"] == 1
        assert data["page_info"]["size"] == 2
        assert data["page_info"]["total_items"] == 5
        assert data["page_info"]["total_pages"] == 3
        assert data["page_info"]["has_next"] is True
        assert data["page_info"]["has_previous"] is False

        # Test second page
        response = client.get("/items?page=2&size=2")
        data = response.json()

        assert response.status_code == 200
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == 3
        assert data["items"][1]["id"] == 4
        assert data["page_info"]["page"] == 2
        assert data["page_info"]["has_next"] is True
        assert data["page_info"]["has_previous"] is True

        # Test last page
        response = client.get("/items?page=3&size=2")
        data = response.json()

        assert response.status_code == 200
        assert len(data["items"]) == 1  # Only one item on the last page
        assert data["items"][0]["id"] == 5
        assert data["page_info"]["page"] == 3
        assert data["page_info"]["has_next"] is False
        assert data["page_info"]["has_previous"] is True
