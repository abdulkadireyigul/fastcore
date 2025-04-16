# Response Schemas

Detailed documentation for API response schemas.

## Overview

Standard response schemas provided by this module:

| Schema | Description | Use Case |
|--------|-------------|----------|
| `BaseResponse[T, M]` | Generic base for all responses | Base class for custom responses |
| `DataResponse[T]` | Single object responses | GET /users/{id} |
| `ListResponse[T]` | Paginated collection responses | GET /users?page=1 |
| `ErrorResponse` | Error responses with details | 4xx/5xx errors |

## Response Examples

### Single Object Response (DataResponse)

GET /users/123:
```json
{
    "success": true,
    "data": {
        "id": 123,
        "name": "John Doe",
        "email": "john@example.com"
    },
    "metadata": {
        "timestamp": "2025-04-15T10:30:00",
        "version": "1.0"
    },
    "message": "User retrieved successfully"
}
```

### List Response with Pagination

GET /users?page=2&page_size=2:
```json
{
    "success": true,
    "data": [
        {
            "id": 3,
            "name": "User 3"
        },
        {
            "id": 4,
            "name": "User 4"
        }
    ],
    "metadata": {
        "timestamp": "2025-04-15T10:30:00",
        "version": "1.0",
        "total": 10,
        "page": 2,
        "page_size": 2,
        "has_next": true,
        "has_previous": true
    },
    "message": "Users retrieved successfully"
}
```

### Error Response

400 Bad Request:
```json
{
    "success": false,
    "data": null,
    "metadata": {
        "timestamp": "2025-04-15T10:30:00",
        "version": "1.0"
    },
    "message": "Validation error",
    "errors": [
        {
            "code": "INVALID_INPUT",
            "message": "Invalid email format",
            "field": "email"
        }
    ]
}
```

## Implementation Guide

### Basic Usage

```python
from fastapi import FastAPI
from fastcore_v2.schemas import DataResponse, ListResponse, ErrorResponse

app = FastAPI()

@app.get("/items/{id}")
def get_item(id: int) -> DataResponse[Item]:
    item = get_item_by_id(id)
    return DataResponse(data=item)

@app.get("/items")
def list_items(page: int = 1) -> ListResponse[Item]:
    items, total = get_items_paginated(page)
    return ListResponse(
        data=items,
        metadata={
            "total": total,
            "page": page
        }
    )
```

### Custom Response Types

To create a custom response type:

```python
from typing import Generic, TypeVar
from fastcore_v2.schemas import BaseResponse
from fastcore_v2.schemas.metadata import ResponseMetadata

T = TypeVar("T")

class StreamResponse(BaseResponse[AsyncIterator[T], ResponseMetadata]):
    """Custom response for streaming data."""
    pass
```