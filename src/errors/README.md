# Errors Module

Provides standardized error handling and exception management for FastAPI applications.

## Features

- Consistent error response structure across your API
- Custom exceptions with status codes, error codes, and messages
- Global exception handlers registered automatically
- Debug mode support (detailed errors in development, sanitized in production)
- Integration with logging system

## Installation

Install the required dependencies:

```bash
poetry add fastapi
```

## Usage

### Raising Errors

Use the provided exception classes to ensure consistent error handling:

```python
from fastapi import APIRouter
from fastcore.errors import AppError, NotFoundError

router = APIRouter()

@router.get("/items/{item_id}")
async def get_item(item_id: str):
    # Example of raising a standard error
    if not item_exists(item_id):
        raise NotFoundError(
            message=f"Item with ID {item_id} not found",
            details={"item_id": item_id}
        )
    
    # Or a generic application error
    if system_overloaded():
        raise AppError(
            status_code=503,
            error_code="SYSTEM_OVERLOADED",
            message="System is currently overloaded, try again later"
        )
    
    return get_item_from_db(item_id)
```

### Custom Exception Classes

Create domain-specific exceptions by extending the base classes:

```python
from fastcore.errors import AppError

class PaymentError(AppError):
    def __init__(
        self,
        message: str = "Payment processing failed",
        error_code: str = "PAYMENT_ERROR",
        status_code: int = 400,
        details: dict = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details
        )
```

### Automatic Error Handling

Error handlers are registered when you use the factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Will register all error handlers
```

Or you can register them manually:

```python
from fastapi import FastAPI
from fastcore.errors import setup_errors
from fastcore.config import get_settings

app = FastAPI()
settings = get_settings()
setup_errors(app, settings)
```

## Error Response Format

All errors follow this standard JSON format:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Item with ID 123 not found",
    "details": {
      "item_id": "123"
    }
  }
}
```

## Built-in Exception Types

- `AppError`: Base exception for all application errors
- `ValidationError`: Input validation errors (status 422)
- `NotFoundError`: Resource not found errors (status 404)
- `UnauthorizedError`: Authentication errors (status 401)
- `ForbiddenError`: Permission errors (status 403)
- `ConflictError`: Resource conflicts (status 409)
- `RateLimitError`: Rate limit exceeded (status 429)
- `ServerError`: Internal server errors (status 500)

## Integration with Logging

All exceptions are automatically logged with appropriate severity levels:
- Client errors (4xx) are logged as warnings
- Server errors (5xx) are logged as errors