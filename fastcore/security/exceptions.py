"""
Security-specific exception classes.

This module provides exceptions for security-related errors,
extending the base exception hierarchy from fastcore.errors.
"""

from typing import Any, Dict, Optional

from fastcore.errors.exceptions import UnauthorizedError


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
