# Errors Module

Standardized error handling for FastAPI applications.

## Features

- Custom exception hierarchy for common API errors
- Automatic conversion of exceptions to standard API responses
- Integration with FastAPI's exception handling
- Simple setup with minimal boilerplate
- Works standalone or integrated with other fastcore_v2 modules

## Usage

### Basic Usage

```python
from fastapi import FastAPI
from fastcore_v2.errors import setup_errors, NotFoundError

app = FastAPI()

# Setup error handling
setup_errors(app)

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    # Simulate item retrieval logic
    if item_id != 42:
        # Raise a custom exception
        raise NotFoundError(
            resource_type="Item", 
            resource_id=item_id
        )
    
    return {"id": item_id, "name": "Example Item"}
```

### With Config and Logging Integration

```python
from fastapi import FastAPI
from fastcore_v2.config import settings
from fastcore_v2.logging import get_logger
from fastcore_v2.errors import setup_errors, ValidationError

app = FastAPI()

# Get logger and setup errors
logger = get_logger(__name__, settings)
setup_errors(app, settings=settings, logger=logger)

@app.post("/items/")
async def create_item(name: str, price: float):
    if price <= 0:
        # Raise validation error with field information
        raise ValidationError(
            message="Invalid item data",
            fields=[
                {
                    "field": "price",
                    "message": "Price must be greater than zero",
                    "code": "INVALID_PRICE"
                }
            ]
        )
    
    logger.info(f"Created item: {name}")
    return {"name": name, "price": price}
```

## Exception Classes

The module provides the following exception classes:

| Exception Class | HTTP Status | Use Case |
|----------------|-------------|----------|
| `AppError` | 500 | Base exception class |
| `ValidationError` | 400 | Data validation errors |
| `NotFoundError` | 404 | Resource not found |
| `UnauthorizedError` | 401 | Authentication errors |
| `ForbiddenError` | 403 | Permission denied |
| `ConflictError` | 409 | Resource conflicts |
| `BadRequestError` | 400 | General client errors |

### ValidationError vs BadRequestError

Both `ValidationError` and `BadRequestError` return a 400 HTTP status code but serve different purposes:

- `ValidationError`: Used specifically for data validation failures, typically when request data doesn't match expected schema. It supports detailed field-level error reporting.

- `BadRequestError`: Used for general client-side errors that aren't specifically related to data validation, such as missing parameters, invalid operations, etc.

### Creating Custom Exceptions

You can create custom exceptions by inheriting from `AppError`:

```python
from fastcore_v2.errors import AppError
from http import HTTPStatus

class RateLimitError(AppError):
    """Exception raised when a rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        **kwargs
    ):
        details = kwargs.pop("details", {}) or {}
        details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            details=details,
            **kwargs
        )
```

## Response Format

Errors are automatically converted into standardized API responses using the `ErrorResponse` schema:

```json
{
  "success": false,
  "message": "Resource not found",
  "errors": [
    {
      "code": "NOT_FOUND",
      "message": "Item with id '123' not found",
      "field": null
    }
  ],
  "metadata": {
    "timestamp": "2025-04-16T12:34:56"
  }
}
```

## API Reference

### Functions

- `setup_errors(app, settings=None, logger=None)` - Main setup function
- `register_exception_handlers(app, logger=None, debug=False)` - Register exception handlers

### Exception Classes

All exception classes have the following attributes:
- `message`: Human-readable error message
- `code`: Error code string identifier
- `status_code`: HTTP status code
- `details`: Dictionary with additional error details