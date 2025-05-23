"""
Error handling module for FastAPI applications.

This module provides standardized error handling including custom exceptions,
error responses, and exception handlers.

Limitations:
- Error response structure is fixed; customization requires code changes.
- No built-in support for localization or multiple languages.
- Only HTTP-style errors are supported (exceptions must inherit from AppError or be handled by FastAPI).
"""

from fastcore.errors.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    DBError,
    ExpiredTokenError,
    ForbiddenError,
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
    RevokedTokenError,
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
    "DBError",
    "InvalidTokenError",
    "ExpiredTokenError",
    "RevokedTokenError",
    "InvalidCredentialsError",
]
