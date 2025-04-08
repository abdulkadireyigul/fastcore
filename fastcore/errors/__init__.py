"""
Error handling utilities for FastAPI applications.

This module provides standardized error handling, including custom exceptions,
error response models, and exception handlers for FastAPI applications.
"""

from fastcore.errors.exceptions import (
    AppError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
)
from fastcore.errors.handlers import (
    register_exception_handlers,
    get_error_responses,
    ErrorResponse,
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