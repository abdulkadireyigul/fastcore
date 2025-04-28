"""
Error handling module for FastAPI applications.

This module provides standardized error handling including custom exceptions,
error responses, and exception handlers.
"""

from fastcore.errors.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from fastcore.errors.handlers import register_exception_handlers
from fastcore.errors.manager import setup_errors

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
