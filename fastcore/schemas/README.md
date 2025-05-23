# Schemas Module

Standardized API response schemas for FastAPI applications that provide consistent data structures for API clients.

## Features

- Standard response envelope format
- Consistent error response structure
- Metadata support for paginated responses
- Type-safe response models with Pydantic
- Reusable base models for common patterns

## Installation

Install the required dependencies:

```bash
poetry add fastapi pydantic
```

## Usage

### Basic Data Response

Use the standard response envelope for successful operations:

```python
from fastapi import APIRouter
from fastcore.schemas import DataResponse
from pydantic import BaseModel

class UserModel(BaseModel):
    id: int
    username: str
    email: str

router = APIRouter()

@router.get("/users/{user_id}", response_model=DataResponse[UserModel])
async def get_user(user_id: int):
    user = await fetch_user(user_id)
    # Returns: {"data": {"id": 1, "username": "john", "email": "john@example.com"}}
    return DataResponse(data=user)
```

### Error Responses

Create consistent error responses:

```python
from fastapi import APIRouter, HTTPException
from fastcore.schemas import ErrorResponse
from fastcore.errors import NotFoundError

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await fetch_user(user_id)
    if not user:
        # Using the ErrorResponse directly
        return ErrorResponse(
            code="USER_NOT_FOUND",
            message=f"User with ID {user_id} not found",
            status_code=404
        )
    
    # Or with exceptions (which are converted to ErrorResponse format)
    if not user.is_active:
        raise NotFoundError(
            message=f"User with ID {user_id} is not active",
            details={"user_id": user_id}
        )
    
    return user
```

### Paginated List Responses

Handle collections with pagination metadata:

```python
from fastapi import APIRouter, Query
from typing import List
from fastcore.schemas import ListResponse
from pydantic import BaseModel

class ProductModel(BaseModel):
    id: int
    name: str
    price: float

router = APIRouter()

@router.get("/products", response_model=ListResponse[ProductModel])
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    # Fetch paginated data
    products, total = await get_products_paginated(page, limit)
    
    # Return with pagination metadata
    return ListResponse(
        data=products,
        metadata={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    )
```

### Generic API Metadata

Include additional metadata in responses:

```python
from fastapi import APIRouter
from fastcore.schemas import DataResponse
from pydantic import BaseModel

class OrderModel(BaseModel):
    id: int
    amount: float
    status: str

router = APIRouter()

@router.get("/orders/{order_id}", response_model=DataResponse[OrderModel])
async def get_order(order_id: int):
    order = await fetch_order(order_id)
    
    # Include metadata with the response
    return DataResponse(
        data=order,
        metadata={
            "processed_at": "2023-04-22T12:34:56Z",
            "transaction_id": "tx_12345",
            "version": "2.0"
        }
    )
```

## Response Model Types

- `ResponseModel`: Base abstract response model
- `DataResponse`: Standard data envelope (`{"data": {}}`)
- `ListResponse`: Paginated list response (`{"data": [], "metadata": {}}`)
- `ErrorResponse`: Error response (`{"error": {"code": "", "message": ""}}`)
- `TokenResponse`: Authentication token response

## Integration with Error Handling

The schemas module works seamlessly with the errors module:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Sets up error handlers that use schemas.ErrorResponse format
```

## Limitations

- Envelope structure is fixed; customization requires subclassing or code changes
- Only basic metadata (timestamp, version, pagination) is included by default
- No built-in support for localization or advanced metadata
- No automatic OpenAPI customization beyond FastAPI defaults

## See Also

For detailed documentation, examples, and implementation guidance on response schemas, see [`schemas/response/README.md`](./response/README.md).