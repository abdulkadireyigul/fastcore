"""
Custom exception classes for FastAPI applications.

This module defines a hierarchy of application-specific exceptions that can be
raised throughout the application and handled consistently by the exception
handlers to produce standardized error responses.
"""

from http import HTTPStatus
from typing import Any, Dict, Optional, Union


class AppError(Exception):
    """
    Base exception for all application errors.
    
    All custom exceptions in the application should inherit from this base class
    to ensure they can be properly handled by the exception handlers.
    
    Attributes:
        status_code: HTTP status code to use in the response
        message: Human-readable error message
        detail: Additional error details (optional)
        headers: HTTP headers to include in the response (optional)
    """
    
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        detail: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize a new application error.
        
        Args:
            message: Human-readable error message
            detail: Additional error details
            headers: HTTP headers to include in the response
        """
        self.message = message
        self.detail = detail
        self.headers = headers
        super().__init__(self.message)


class NotFoundError(AppError):
    """
    Error raised when a requested resource cannot be found.
    
    Example:
        ```python
        if not user:
            raise NotFoundError("User not found", {"user_id": user_id})
        ```
    """
    
    status_code = HTTPStatus.NOT_FOUND
    
    def __init__(
        self,
        message: str = "Resource not found",
        detail: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize a new not found error."""
        super().__init__(message, detail, headers)


class ValidationError(AppError):
    """
    Error raised when input data fails validation.
    
    Example:
        ```python
        if not validate_email(email):
            raise ValidationError("Invalid email format", {"email": email})
        ```
    """
    
    status_code = HTTPStatus.BAD_REQUEST
    
    def __init__(
        self,
        message: str = "Validation error",
        detail: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize a new validation error."""
        super().__init__(message, detail, headers)


class AuthenticationError(AppError):
    """
    Error raised when authentication fails.
    
    Example:
        ```python
        if not verify_token(token):
            raise AuthenticationError("Invalid or expired token")
        ```
    """
    
    status_code = HTTPStatus.UNAUTHORIZED
    
    def __init__(
        self,
        message: str = "Authentication required",
        detail: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize a new authentication error."""
        # Add WWW-Authenticate header as required by HTTP 401
        if headers is None:
            headers = {}
        if "WWW-Authenticate" not in headers:
            headers["WWW-Authenticate"] = "Bearer"
        super().__init__(message, detail, headers)


class AuthorizationError(AppError):
    """
    Error raised when a user lacks permission to perform an action.
    
    Example:
        ```python
        if not user.has_permission("delete"):
            raise AuthorizationError("Insufficient permissions to delete resource")
        ```
    """
    
    status_code = HTTPStatus.FORBIDDEN
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        detail: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize a new authorization error."""
        super().__init__(message, detail, headers)


class ConflictError(AppError):
    """
    Error raised when a conflict occurs (e.g., duplicate resource).
    
    Example:
        ```python
        if db.exists(User, email=user.email):
            raise ConflictError("User with this email already exists")
        ```
    """
    
    status_code = HTTPStatus.CONFLICT
    
    def __init__(
        self,
        message: str = "Resource conflict",
        detail: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize a new conflict error."""
        super().__init__(message, detail, headers)


class DatabaseError(AppError):
    """
    Error raised when a database operation fails.
    
    Example:
        ```python
        try:
            db.execute(query)
        except SQLAlchemyError as e:
            raise DatabaseError(f"Database error: {str(e)}")
        ```
    """
    
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    
    def __init__(
        self,
        message: str = "Database operation failed",
        detail: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize a new database error."""
        super().__init__(message, detail, headers)