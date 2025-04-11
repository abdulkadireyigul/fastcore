"""
Example FastAPI application using FastCore.

This is a minimal example of how to use FastCore to quickly bootstrap
a new FastAPI application with all components pre-configured.
"""

from typing import List, Optional

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel

from fastcore.api.responses import (
    BaseResponse,
    FilterInfo,
    ListResponse,
    SortInfo,
    create_response,
)
from fastcore.app_factory import create_app
from fastcore.config.base import Environment
from fastcore.db.session import Session, get_db

# Create app with all components enabled
app = create_app(
    env=Environment.DEVELOPMENT,
    enable_cors=True,
    enable_database=True,
    enable_error_handlers=True,
    db_echo=True,  # SQL logging for development
)


# Example model
class Item(BaseModel):
    id: int
    name: str
    category: str
    price: float


# Example data access (in a real app, this would use SQLAlchemy models)
def get_items(
    db: Session, category: Optional[str] = None, min_price: Optional[float] = None
):
    # Simulate database with some sample items
    items = [
        Item(id=1, name="Item 1", category="A", price=10.0),
        Item(id=2, name="Item 2", category="B", price=20.0),
        Item(id=3, name="Item 3", category="A", price=30.0),
        Item(id=4, name="Item 4", category="C", price=40.0),
        Item(id=5, name="Item 5", category="B", price=50.0),
    ]

    # Apply filters if provided
    if category:
        items = [item for item in items if item.category == category]
    if min_price is not None:
        items = [item for item in items if item.price >= min_price]

    return items


# Example routes using standardized responses
@app.get("/", response_model=BaseResponse[dict])
def read_root():
    """Example of a simple response using BaseResponse."""
    return create_response(
        data={"message": "Welcome to FastAPI powered by FastCore!"},
        message="API is operational",
    )


@app.get("/items/", response_model=ListResponse[Item])
def read_items(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Filter by minimum price"),
    sort_by: Optional[str] = Query(None, description="Sort field (name, price)"),
    sort_dir: Optional[str] = Query("asc", description="Sort direction (asc, desc)"),
    page: Optional[int] = Query(1, ge=1, description="Page number"),
    page_size: Optional[int] = Query(10, ge=1, le=100, description="Items per page"),
):
    """Example of an enhanced list response using ListResponse."""
    # Get filtered items
    items = get_items(db, category, min_price)
    total_count = len(items)

    # Apply sorting
    if sort_by:
        reverse = sort_dir.lower() == "desc"
        items.sort(key=lambda x: getattr(x, sort_by), reverse=reverse)

    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    # Collect applied filters
    applied_filters = []
    if category:
        applied_filters.append(
            FilterInfo(field="category", operator="equals", value=category)
        )
    if min_price:
        applied_filters.append(
            FilterInfo(field="price", operator="greater_or_equal", value=min_price)
        )

    # Collect sorting info
    applied_sorting = None
    if sort_by:
        applied_sorting = [SortInfo(field=sort_by, direction=sort_dir)]

    # Create aggregations (e.g., count by category)
    aggregations = {
        "categories": {
            cat: len([i for i in items if i.category == cat])
            for cat in set(i.category for i in items)
        }
    }

    return create_response(
        data=page_items,
        message="Items retrieved successfully",
        list_metadata={
            "total_count": total_count,
            "filtered_count": len(items),
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": end < total_count,
            "has_previous": page > 1,
        },
        applied_filters=[f.dict() for f in applied_filters]
        if applied_filters
        else None,
        applied_sorting=[s.dict() for s in applied_sorting]
        if applied_sorting
        else None,
        aggregations=aggregations,
    )


@app.get("/error")
def trigger_error():
    """Example of error handling with standardized error responses."""
    # This will be caught by the exception handlers and formatted consistently
    raise ValueError("Example error")
