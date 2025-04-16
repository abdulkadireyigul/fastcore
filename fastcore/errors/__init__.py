"""
Error handling module for FastAPI applications.

This module provides standardized error handling including custom exceptions,
error responses, and exception handlers.
"""

from .exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from .handlers import register_exception_handlers
from .manager import setup_errors

__all__ = [
    # Main setup function
    "setup_errors",
    # Handler registration
    "register_exception_handlers",
    # Exception classes
    "AppError",
    "ValidationError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "ConflictError",
    "BadRequestError",
]
