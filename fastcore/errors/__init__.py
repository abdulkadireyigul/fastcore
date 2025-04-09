"""
Error handling utilities for FastAPI applications.

This module provides standardized error handling, including custom exceptions,
error response models, and exception handlers for FastAPI applications.
"""

from fastcore.errors.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)
from fastcore.errors.handlers import (
    ErrorResponse,
    get_error_responses,
    register_exception_handlers,
)

__all__ = [
    # Base exceptions
    "AppError",
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DatabaseError",
    # Handlers
    "register_exception_handlers",
    "get_error_responses",
    "ErrorResponse",
]
