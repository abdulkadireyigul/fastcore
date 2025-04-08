"""
Tests for error handlers integration with FastAPI.
"""
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from fastcore.errors.exceptions import (
    AppError,
    NotFoundError,
    ValidationError,
)
from fastcore.errors.handlers import (
    ErrorResponse,
    _handle_app_error,
    _handle_http_exception,
    _handle_python_exception,
    _handle_validation_error,
    get_error_responses,
    register_exception_handlers,
)


class TestErrorResponse:
    """Tests for the ErrorResponse model."""

    def test_model_creation(self):
        """Test ErrorResponse model creation with valid data."""
        response = ErrorResponse(
            status=404,
            code="NOT_FOUND",
            message="Resource not found",
            detail={"id": "missing"},
            path="/api/resource/123",
        )
        assert response.status == 404
        assert response.code == "NOT_FOUND"
        assert response.message == "Resource not found"
        assert response.detail == {"id": "missing"}
        assert response.path == "/api/resource/123"

    def test_model_serialization(self):
        """Test model serialization to dict."""
        response = ErrorResponse(
            status=404,
            code="NOT_FOUND",
            message="Resource not found",
            detail={"id": "missing"},
            path="/api/resource/123",
        )
        data = response.model_dump()
        assert data["status"] == 404
        assert data["code"] == "NOT_FOUND"
        assert data["message"] == "Resource not found"
        assert data["detail"] == {"id": "missing"}
        assert data["path"] == "/api/resource/123"


class TestAppErrorHandler:
    """Tests for handling AppError exceptions."""

    def test_handle_app_error(self):
        """Test handling of AppError with default settings."""
        # Create mock request
        request = MagicMock()
        request.url.path = "/api/test"
        
        # Create error
        error = NotFoundError(message="User not found", detail={"user_id": 123})
        
        # Mock settings with debug mode disabled
        with patch("fastcore.errors.handlers._get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.API.DEBUG = False
            mock_get_settings.return_value = mock_settings
            
            # Call handler
            response = _handle_app_error(request, error)
            
            # Verify response
            assert response.status_code == HTTPStatus.NOT_FOUND.value
            response_body = response.body.decode()
            assert "User not found" in response_body
            assert "NOT_FOUND" in response_body
            assert "user_id" in response_body
            assert "/api/test" in response_body

    def test_handle_app_error_with_debug(self):
        """Test handling of AppError with debug mode enabled."""
        # Create mock request
        request = MagicMock()
        request.url.path = "/api/test"
        
        # Create error without detail
        error = AppError(message="Something went wrong")
        
        # Mock settings with debug mode enabled
        with patch("fastcore.errors.handlers._get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.API.DEBUG = True
            mock_get_settings.return_value = mock_settings
            
            # Call handler
            response = _handle_app_error(request, error)
            
            # Verify response includes traceback
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR.value
            response_body = response.body.decode()
            assert "traceback" in response_body


class TestHTTPExceptionHandler:
    """Tests for handling FastAPI's HTTPException."""

    def test_handle_http_exception(self):
        """Test handling of HTTPException."""
        # Create mock request
        request = MagicMock()
        request.url.path = "/api/test"
        
        # Create error
        headers = {"X-Error-Code": "CUSTOM_ERROR"}
        error = HTTPException(status_code=404, detail="Resource not found", headers=headers)
        
        # Call handler
        response = _handle_http_exception(request, error)
        
        # Verify response
        assert response.status_code == 404
        response_body = response.body.decode()
        assert "Resource not found" in response_body
        assert "NOT_FOUND" in response_body
        assert response.headers.get("X-Error-Code") == "CUSTOM_ERROR"


class TestValidationErrorHandler:
    """Tests for handling FastAPI's RequestValidationError."""

    def test_handle_validation_error(self):
        """Test handling of RequestValidationError."""
        # Create mock request
        request = MagicMock()
        request.url.path = "/api/test"
        
        # Create validation error (simplified)
        error = RequestValidationError(
            errors=[
                {
                    "loc": ("body", "email"),
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ]
        )
        
        # Call handler
        response = _handle_validation_error(request, error)
        
        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_body = response.body.decode()
        assert "Request validation error" in response_body
        assert "UNPROCESSABLE" in response_body
        assert "body -> email" in response_body
        assert "field required" in response_body


class TestPythonExceptionHandler:
    """Tests for handling general Python exceptions."""

    def test_handle_python_exception_no_debug(self):
        """Test handling of general exceptions with debug mode off."""
        # Create mock request
        request = MagicMock()
        request.url.path = "/api/test"
        
        # Create a Python exception
        error = ValueError("Invalid value")
        
        # Mock settings with debug mode disabled
        with patch("fastcore.errors.handlers._get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.API.DEBUG = False
            mock_get_settings.return_value = mock_settings
            
            # Call handler
            response = _handle_python_exception(request, error)
            
            # Verify response
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR.value
            response_body = response.body.decode()
            assert "Internal server error" in response_body
            assert "INTERNAL_SERVER_ERROR" in response_body

    def test_handle_python_exception_with_debug(self):
        """Test handling of general exceptions with debug mode on."""
        # Create mock request
        request = MagicMock()
        request.url.path = "/api/test"
        
        # Create a Python exception
        error = ValueError("Invalid value")
        
        # Mock settings with debug mode enabled
        with patch("fastcore.errors.handlers._get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.API.DEBUG = True
            mock_get_settings.return_value = mock_settings
            
            # Call handler
            response = _handle_python_exception(request, error)
            
            # Verify response includes debug information
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR.value
            response_body = response.body.decode()
            assert "Internal server error" in response_body
            assert "type" in response_body
            assert "ValueError" in response_body
            assert "traceback" in response_body


class TestRegisterExceptionHandlers:
    """Tests for registering exception handlers with a FastAPI app."""

    def test_register_exception_handlers(self):
        """Test registration of exception handlers."""
        app = FastAPI()
        original_handlers_count = len(app.exception_handlers)
        
        # Register handlers
        register_exception_handlers(app)
        
        # Verify handlers were added
        assert len(app.exception_handlers) > original_handlers_count
        
        # Check for handlers - FastAPI might use either starlette.exceptions.HTTPException
        # or fastapi.exceptions.HTTPException, so we need to check for both
        http_exception_registered = False
        for exc_type, handler in app.exception_handlers.items():
            if exc_type == HTTPException or str(exc_type).endswith("HTTPException"):
                http_exception_registered = True
                break
        assert http_exception_registered, "No HTTP exception handler was registered"
        
        # Check other handlers
        assert any(issubclass(exc_type, RequestValidationError) for exc_type, _ in app.exception_handlers.items())
        assert any(issubclass(exc_type, AppError) for exc_type, _ in app.exception_handlers.items())
        assert any(exc_type == Exception for exc_type, _ in app.exception_handlers.items())


class TestGetErrorResponses:
    """Tests for generating OpenAPI error response documentation."""

    def test_get_error_responses_with_specified_exceptions(self):
        """Test generation of error responses for specified exceptions."""
        responses = get_error_responses(NotFoundError, ValidationError)
        
        # Should include responses for specified exceptions
        assert HTTPStatus.NOT_FOUND.value in responses
        assert HTTPStatus.BAD_REQUEST.value in responses
        
        # Should not include responses for unspecified exceptions
        assert HTTPStatus.UNAUTHORIZED.value not in responses
        
        # Check response model and description
        assert responses[HTTPStatus.NOT_FOUND.value]["model"] == ErrorResponse
        assert "not found" in responses[HTTPStatus.NOT_FOUND.value]["description"].lower()

    def test_get_error_responses_with_no_exceptions(self):
        """Test generation of error responses with no specified exceptions."""
        responses = get_error_responses()
        
        # Should include responses for common exceptions
        assert HTTPStatus.NOT_FOUND.value in responses
        assert HTTPStatus.BAD_REQUEST.value in responses
        assert HTTPStatus.UNAUTHORIZED.value in responses
        assert HTTPStatus.FORBIDDEN.value in responses
        assert HTTPStatus.CONFLICT.value in responses
        assert HTTPStatus.INTERNAL_SERVER_ERROR.value in responses