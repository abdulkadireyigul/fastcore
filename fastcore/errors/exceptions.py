"""
Base exception classes for FastAPI applications.

This module provides a standardized exception hierarchy that can be 
used throughout applications. These exceptions are designed to be 
converted into appropriate HTTP responses.
"""

from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union


class AppError(Exception):
    """
    Base exception for all application errors.

    All custom exceptions should inherit from this class.

    Attributes:
        message: Human-readable error message
        code: Error code identifier (default: ERROR)
        status_code: HTTP status code (default: 500)
        details: Additional error details
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "ERROR",
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppError):
    """
    Exception raised when validation fails.

    Attributes:
        fields: List of field-specific validation errors
    """

    def __init__(
        self,
        message: str = "Validation error",
        fields: Optional[List[Dict[str, Any]]] = None,
        code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        # Store fields both as an instance attribute for direct access
        # and in the details dictionary for serialization
        self.fields = fields or []
        if fields:
            details = details or {}
            details["fields"] = fields

        super().__init__(
            message=message,
            code=code,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details,
        )


class NotFoundError(AppError):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        code: str = "NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        if resource_type and resource_id:
            message = f"{resource_type} with id '{resource_id}' not found"
            details = details or {}
            details.update({"resource_type": resource_type, "resource_id": resource_id})

        super().__init__(
            message=message,
            code=code,
            status_code=HTTPStatus.NOT_FOUND,
            details=details,
        )


class UnauthorizedError(AppError):
    """Exception raised when authentication fails or is missing."""

    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "UNAUTHORIZED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=HTTPStatus.UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(AppError):
    """Exception raised when user lacks permission for an action."""

    def __init__(
        self,
        message: str = "Permission denied",
        code: str = "FORBIDDEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=HTTPStatus.FORBIDDEN,
            details=details,
        )


class ConflictError(AppError):
    """Exception raised for resource conflicts (e.g., duplicate entries)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        code: str = "CONFLICT",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message, code=code, status_code=HTTPStatus.CONFLICT, details=details
        )


class BadRequestError(AppError):
    """Exception raised for general client-side errors."""

    def __init__(
        self,
        message: str = "Bad request",
        code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details,
        )


class DBError(AppError):
    """
    Exception raised for database-related errors.
    """

    def __init__(
        self,
        message: str = "Database error",
        code: str = "DB_ERROR",
        details: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details,
        )


# Exception classes for security-related errors
class InvalidTokenError(UnauthorizedError):
    """Exception raised when a token is malformed or invalid."""

    def __init__(
        self,
        message: str = "Invalid token",
        code: str = "INVALID_TOKEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details)


class ExpiredTokenError(UnauthorizedError):
    """Exception raised when a token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        code: str = "EXPIRED_TOKEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details)


class RevokedTokenError(UnauthorizedError):
    """Exception raised when a revoked token is used."""

    def __init__(
        self,
        message: str = "Token has been revoked",
        code: str = "REVOKED_TOKEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details)


class InvalidCredentialsError(UnauthorizedError):
    """Exception raised when login credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid credentials",
        code: str = "INVALID_CREDENTIALS",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details)
