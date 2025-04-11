"""
Tests for the response models.

This module contains tests for the response models, including
BaseResponse, ListResponse, and error responses.
"""

from datetime import datetime
from typing import List, Optional

import pytest
from fastapi import Depends, FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastcore.api.filtering import FilterInfo, FilterParams
from fastcore.api.pagination import PaginationParams, paginate
from fastcore.api.responses import (
    BaseResponse,
    ErrorDetail,
    ErrorResponse,
    ListMetadata,
    ListResponse,
    ResponseMetadata,
    SortInfo,
    create_response,
)
from fastcore.api.sorting import SortParams


class TestResponseModels:
    """Tests for the response models."""

    def test_base_response(self):
        """Test the base response model."""
        response = BaseResponse[dict](
            success=True, data={"key": "value"}, message="Test message"
        )
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Test message"
        assert isinstance(response.metadata, ResponseMetadata)
        assert response.errors is None

    def test_list_response(self):
        """Test the list response model."""
        items = [1, 2, 3]
        metadata = ListMetadata(
            total_count=10,
            filtered_count=3,
            page=1,
            page_size=3,
            total_pages=4,
            has_next=True,
            has_previous=False,
        )
        filters = [FilterInfo(field="type", operator="equals", value="test")]
        sorting = [SortInfo(field="id", direction="asc")]

        response = ListResponse[int](
            success=True,
            data=items,
            list_metadata=metadata,
            applied_filters=filters,
            applied_sorting=sorting,
            aggregations={"total": 10},
            message="Test list",
        )

        assert response.success is True
        assert response.data == items
        assert response.message == "Test list"
        assert response.list_metadata == metadata
        assert response.applied_filters == filters
        assert response.applied_sorting == sorting
        assert response.aggregations == {"total": 10}

    def test_error_response(self):
        """Test the error response model."""
        error = ErrorDetail(
            code="NOT_FOUND", message="Item not found", field="id", details={"id": 123}
        )
        response = ErrorResponse(
            success=False, errors=[error], message="Error occurred"
        )

        assert response.success is False
        assert len(response.errors) == 1
        assert response.errors[0] == error
        assert response.message == "Error occurred"


class TestCreateResponse:
    """Tests for the create_response function."""

    def test_create_simple_response(self):
        """Test creating a simple response."""
        response = create_response(data={"key": "value"}, message="Test message")
        data = response.body.decode()
        assert '"success":true' in data
        assert '"message":"Test message"' in data
        assert '"key":"value"' in data
        assert response.status_code == 200

    def test_create_list_response(self):
        """Test creating a list response."""
        items = [1, 2, 3]
        filters = [{"field": "type", "operator": "equals", "value": "test"}]
        sorting = [{"field": "id", "direction": "asc"}]

        response = create_response(
            data=items,
            message="Test list",
            list_metadata={
                "total_count": 10,
                "filtered_count": 3,
                "page": 1,
                "page_size": 3,
            },
            applied_filters=filters,
            applied_sorting=sorting,
            aggregations={"total": 10},
        )

        data = response.body.decode()
        assert '"success":true' in data
        assert '"message":"Test list"' in data
        assert '"total_count":10' in data
        assert '"filtered_count":3' in data
        assert '"field":"type"' in data
        assert '"operator":"equals"' in data
        assert '"field":"id"' in data
        assert '"direction":"asc"' in data


class TestIntegration:
    """Integration tests for responses with filtering, sorting, and pagination."""

    def test_full_list_endpoint(self):
        """Test a complete list endpoint with all features."""
        app = FastAPI()

        class Item(BaseModel):
            id: int
            name: str
            category: str
            price: float

        @app.get("/items", response_model=ListResponse[Item])
        def list_items(
            pagination: PaginationParams = Depends(),
            filters: FilterParams = Depends(
                FilterParams(allowed_fields={"category", "price"})
            ),
            sort: SortParams = Depends(SortParams(allowed_fields={"name", "price"})),
        ):
            # Sample data
            all_items = [
                Item(id=1, name="A", category="cat1", price=10.0),
                Item(id=2, name="B", category="cat2", price=20.0),
                Item(id=3, name="C", category="cat1", price=30.0),
                Item(id=4, name="D", category="cat2", price=40.0),
            ]

            # Apply filtering
            items = all_items
            if filters.filters:
                items = [
                    item
                    for item in items
                    if any(getattr(item, f.field) == f.value for f in filters.filters)
                ]

            # Apply sorting
            if sort.sort_by:
                for field in reversed(sort.sort_by):
                    reverse = field.direction == "desc"
                    items.sort(key=lambda x: getattr(x, field.field), reverse=reverse)

            # Get total counts
            total_count = len(all_items)
            filtered_count = len(items)

            # Apply pagination
            start = pagination.get_skip()
            end = start + pagination.get_limit()
            page_items = items[start:end]

            # Calculate aggregations
            aggregations = {
                "categories": {
                    cat: len([i for i in items if i.category == cat])
                    for cat in {"cat1", "cat2"}
                },
                "price_ranges": {
                    "0-20": len([i for i in items if i.price <= 20]),
                    "21-40": len([i for i in items if 20 < i.price <= 40]),
                },
            }

            return paginate(
                items=page_items,
                params=pagination,
                total_items=total_count,
                filtered_count=filtered_count,
                applied_filters=filters.filters,
                applied_sorting=sort.sort_by,
                aggregations=aggregations,
                message="Items retrieved successfully",
            )

        client = TestClient(app)

        # Test with all features
        response = client.get(
            "/items?page=1&size=2" "&filter=category:eq:cat1" "&sort_by=price:desc"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["list_metadata"]["total_count"] == 4
        assert data["list_metadata"]["filtered_count"] == 2
        assert data["list_metadata"]["page"] == 1
        assert data["list_metadata"]["has_next"] is False

        # Verify sorting
        assert data["data"][0]["price"] == 30.0  # Highest price first
        assert len(data["applied_sorting"]) == 1
        assert data["applied_sorting"][0]["direction"] == "desc"

        # Verify filtering
        assert len(data["applied_filters"]) == 1
        assert data["applied_filters"][0]["field"] == "category"
        assert data["applied_filters"][0]["value"] == "cat1"

        # Verify aggregations
        assert "categories" in data["aggregations"]
        assert data["aggregations"]["categories"]["cat1"] == 2
        assert "price_ranges" in data["aggregations"]
