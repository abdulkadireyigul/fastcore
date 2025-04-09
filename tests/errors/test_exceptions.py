"""
Tests for custom exception classes.
"""
from http import HTTPStatus

import pytest

from fastcore.errors.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)


class TestAppError:
    """Tests for the base AppError class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        error = AppError()
        assert error.message == "An unexpected error occurred"
        assert error.detail is None
        assert error.headers is None
        assert error.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert str(error) == "An unexpected error occurred"

    def test_init_with_args(self):
        """Test initialization with custom arguments."""
        message = "Custom error message"
        detail = {"field": "value"}
        headers = {"X-Custom-Header": "Value"}
        error = AppError(message=message, detail=detail, headers=headers)
        assert error.message == message
        assert error.detail == detail
        assert error.headers == headers


class TestNotFoundError:
    """Tests for the NotFoundError class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        error = NotFoundError()
        assert error.message == "Resource not found"
        assert error.status_code == HTTPStatus.NOT_FOUND

    def test_init_with_args(self):
        """Test initialization with custom arguments."""
        message = "User not found"
        detail = {"user_id": 123}
        error = NotFoundError(message=message, detail=detail)
        assert error.message == message
        assert error.detail == detail
        assert error.status_code == HTTPStatus.NOT_FOUND


class TestValidationError:
    """Tests for the ValidationError class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        error = ValidationError()
        assert error.message == "Validation error"
        assert error.status_code == HTTPStatus.BAD_REQUEST

    def test_init_with_args(self):
        """Test initialization with custom arguments."""
        message = "Invalid email format"
        detail = {"email": "invalid-email"}
        error = ValidationError(message=message, detail=detail)
        assert error.message == message
        assert error.detail == detail
        assert error.status_code == HTTPStatus.BAD_REQUEST


class TestAuthenticationError:
    """Tests for the AuthenticationError class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        error = AuthenticationError()
        assert error.message == "Authentication required"
        assert error.status_code == HTTPStatus.UNAUTHORIZED
        assert error.headers == {"WWW-Authenticate": "Bearer"}

    def test_init_with_custom_headers(self):
        """Test initialization with custom headers."""
        headers = {"WWW-Authenticate": "Basic", "X-Custom": "Value"}
        error = AuthenticationError(headers=headers)
        assert error.headers == headers
        # WWW-Authenticate header should not be overridden
        assert error.headers["WWW-Authenticate"] == "Basic"


class TestAuthorizationError:
    """Tests for the AuthorizationError class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        error = AuthorizationError()
        assert error.message == "Insufficient permissions"
        assert error.status_code == HTTPStatus.FORBIDDEN

    def test_init_with_args(self):
        """Test initialization with custom arguments."""
        message = "You don't have permission to delete this resource"
        error = AuthorizationError(message=message)
        assert error.message == message
        assert error.status_code == HTTPStatus.FORBIDDEN


class TestConflictError:
    """Tests for the ConflictError class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        error = ConflictError()
        assert error.message == "Resource conflict"
        assert error.status_code == HTTPStatus.CONFLICT

    def test_init_with_args(self):
        """Test initialization with custom arguments."""
        message = "User with this email already exists"
        error = ConflictError(message=message)
        assert error.message == message
        assert error.status_code == HTTPStatus.CONFLICT


class TestDatabaseError:
    """Tests for the DatabaseError class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        error = DatabaseError()
        assert error.message == "Database operation failed"
        assert error.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_init_with_args(self):
        """Test initialization with custom arguments."""
        message = "Failed to insert record"
        error = DatabaseError(message=message)
        assert error.message == message
        assert error.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
