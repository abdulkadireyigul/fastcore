"""
Error handling utilities for FastAPI applications.

This module provides standardized error handling, including custom exceptions,
error response models, and exception handlers for FastAPI applications.
"""

import traceback
from http import HTTPStatus
from typing import Any, Callable, Dict, List, Optional, Type, Union

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastcore.api.responses import create_response
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from fastcore.errors.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
)
from fastcore.errors.exceptions import ValidationError as AppValidationError
from fastcore.logging import get_logger

logger = get_logger(__name__)


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Model for error responses."""

    success: bool = False
    message: str
    errors: List[ErrorDetail] = []
    status: int
    code: str
    detail: Optional[Dict[str, Any]] = None
    path: str

    def dict(self, *args, **kwargs):
        """Backward compatibility with Pydantic v1."""
        if hasattr(super(), "model_dump"):
            return super().model_dump(*args, **kwargs)
        return super().dict(*args, **kwargs)

    def model_dump(self, *args, **kwargs):
        """Forward compatibility with Pydantic v2."""
        if hasattr(super(), "dict"):
            return super().dict(*args, **kwargs)
        return super().model_dump(*args, **kwargs)


def _get_settings(request: Request):
    """Get application settings from request state."""
    if not hasattr(request.app.state, "settings"):
        return None
    return request.app.state.settings


def _create_error_response(
    status_code: int,
    code: str,
    message: str,
    detail: Any = None,
    path: str = "",
) -> ErrorResponse:
    """Create a standardized error response."""
    error = ErrorDetail(
        code=code,
        message=message,
        details={"path": path} if path else None,
    )

    if detail:
        if isinstance(detail, dict):
            error.details = {**error.details, **detail} if error.details else detail
        elif isinstance(detail, list):
            error.details = {"errors": detail}
        else:
            error.details = {"detail": str(detail)}

    return ErrorResponse(
        success=False,
        errors=[error],
        message=message,
        status=status_code,
        code=code,
        detail=error.details,
        path=path,
    )


def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Handle application-specific errors."""
    settings = _get_settings(request)
    debug_mode = settings and getattr(settings.API, "DEBUG", False)

    details = {"path": request.url.path}
    if hasattr(exc, "detail") and exc.detail:
        details.update(
            exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
        )

    if debug_mode:
        details["traceback"] = "".join(traceback.format_tb(exc.__traceback__))

    # Special handling for NotFoundError
    if isinstance(exc, NotFoundError):
        code = "NOT_FOUND"
    else:
        code = exc.__class__.__name__.replace("Error", "").upper()

    error_response = _create_error_response(
        status_code=exc.status_code.value,
        code=code,
        message=str(exc),
        detail=details,
        path=request.url.path,
    )

    return create_response(
        success=False,
        errors=jsonable_encoder(error_response.errors),
        message=str(exc),
        status_code=exc.status_code.value,
    )


def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    errors = []
    for error in exc.errors():
        loc = error["loc"]
        field = " -> ".join(str(x) for x in loc)
        error_detail = ErrorDetail(
            code="UNPROCESSABLE_ENTITY",
            message=error["msg"],
            field=field,
            details=error,
        )
        errors.append(error_detail)

    return create_response(
        success=False,
        errors=jsonable_encoder(errors),
        message="Request validation error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def _handle_http_error(
    request: Request, exc: Union[StarletteHTTPException, FastAPIHTTPException]
) -> JSONResponse:
    """Handle HTTP exceptions."""
    code = "NOT_FOUND" if exc.status_code == 404 else f"HTTP_{exc.status_code}"
    error_response = _create_error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
        path=request.url.path,
    )

    response = create_response(
        success=False,
        errors=jsonable_encoder(
            [
                {
                    "code": code,
                    "message": str(exc.detail),
                    "details": {"path": request.url.path},
                }
            ]
        ),
        message=str(exc.detail),
        status_code=exc.status_code,
    )

    # Add any custom headers from the exception
    if hasattr(exc, "headers") and exc.headers:
        response.headers.update(exc.headers)

    return response


def _handle_pydantic_error(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        loc = error["loc"]
        field = " -> ".join(str(x) for x in loc)
        error_detail = ErrorDetail(
            code="UNPROCESSABLE_ENTITY",
            message=error["msg"],
            field=field,
            details=error,
        )
        errors.append(error_detail)

    return create_response(
        success=False,
        errors=jsonable_encoder(errors),
        message="Data validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def _handle_python_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle general Python exceptions."""
    # Get exception details
    exc_type = exc.__class__.__name__
    exc_message = str(exc)
    exc_traceback = "".join(traceback.format_tb(exc.__traceback__))

    # Log the error
    logger.error(
        f"Unhandled {exc_type} at {request.url.path}: {exc_message}\n{exc_traceback}"
    )

    # Create error details
    details = {
        "type": exc_type,
        "message": exc_message,
        "path": request.url.path,
    }

    # Add traceback in debug mode
    settings = _get_settings(request)
    if settings and getattr(settings.API, "DEBUG", False):
        details["traceback"] = exc_traceback

    # Create the error response
    error_response = _create_error_response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
        detail=details,
        path=request.url.path,
    )

    return create_response(
        success=False,
        errors=jsonable_encoder(error_response.errors),
        message="Internal server error",
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    )


# Dictionary mapping exception types to their handlers
exception_handlers: Dict[Type[Exception], Callable] = {
    AppError: _handle_app_error,
    StarletteHTTPException: _handle_http_error,
    FastAPIHTTPException: _handle_http_error,
    RequestValidationError: _handle_validation_error,
    ValidationError: _handle_pydantic_error,
    Exception: _handle_python_exception,
}


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with a FastAPI application.

    This function sets up exception handlers for built-in FastAPI exceptions
    as well as custom application exceptions.

    Args:
        app: FastAPI application instance

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.errors import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
        ```
    """
    # Register all handlers from the exception_handlers dictionary
    for exc_class, handler in exception_handlers.items():
        app.add_exception_handler(exc_class, handler)

    # Log registration
    logger.info("Registered exception handlers")


def get_error_responses(
    *exception_classes: Type[Exception],
) -> Dict[Union[int, str], Dict[str, Any]]:
    """
    Generate OpenAPI error response definitions for documentation.

    This function helps to document the possible error responses from
    an endpoint in the OpenAPI schema.

    Args:
        *exception_classes: One or more exception classes to document

    Returns:
        Dictionary mapping status codes to response schemas

    Example:
        ```python
        @app.get(
            "/users/{user_id}",
            responses=get_error_responses(NotFoundError, AuthenticationError)
        )
        def get_user(user_id: int):
            # Function implementation
            pass
        ```
    """
    responses: Dict[Union[int, str], Dict[str, Any]] = {}

    # If no exceptions specified, include general error responses
    if not exception_classes:
        exception_classes = (
            AppValidationError,
            NotFoundError,
            AuthenticationError,
            AuthorizationError,
            ConflictError,
            DatabaseError,
        )

    # Generate responses for each exception class
    for exc_class in exception_classes:
        if hasattr(exc_class, "status_code"):
            status_code = getattr(exc_class, "status_code").value
        else:
            status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value

        # Add response schema for this status code
        responses[status_code] = {
            "model": ErrorResponse,
            "description": getattr(exc_class, "__doc__", "").strip()
            or exc_class.__name__,
        }

    return responses
