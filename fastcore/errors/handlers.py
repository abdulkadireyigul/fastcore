"""
Exception handlers for FastAPI applications.

This module provides utilities to register exception handlers with FastAPI
applications and generate standardized error responses.
"""

import traceback
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from fastcore.config.app import AppSettings, Environment
from fastcore.errors.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)


class ErrorResponse(BaseModel):
    """
    Standard error response model for API errors.
    
    This model defines the structure of error responses returned by
    the API when exceptions occur.
    
    Attributes:
        status: HTTP status code
        code: Error code (matches the HTTP status code by default)
        message: Human-readable error message
        detail: Additional details about the error (optional)
        path: URL path where the error occurred
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    status: int = Field(description="HTTP status code")
    code: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    detail: Optional[Union[Dict[str, Any], List[Dict[str, Any]], str]] = Field(
        None, description="Additional error details"
    )
    path: str = Field(description="URL path where the error occurred")
    
    def model_dump(self) -> Dict[str, Any]:
        """
        Convert model to dictionary, supporting both Pydantic v1 and v2.
        
        Returns:
            Dictionary representation of the model
        """
        # Support both Pydantic v1 and v2
        result = {}
        if hasattr(super(), "model_dump"):
            result = super().model_dump(exclude={"model_config"})
        elif hasattr(super(), "dict"):
            result = super().dict(exclude={"model_config"})  # type: ignore
        else:
            # Fallback implementation
            result = {
                "status": self.status,
                "code": self.code,
                "message": self.message,
                "detail": self.detail,
                "path": self.path,
            }
        
        # Ensure model_config isn't included
        if "model_config" in result:
            del result["model_config"]
            
        return result


def _get_settings() -> AppSettings:
    """
    Get application settings.
    
    Returns:
        Application settings based on the current environment
    """
    # Try to detect environment or default to development
    env_name = "development"
    try:
        import os
        env_name = os.environ.get("APP_ENVIRONMENT", "development")
        env = Environment(env_name.lower())
    except ValueError:
        env = Environment.DEVELOPMENT
    
    return AppSettings.load(env)


def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """
    Handle application-specific exceptions.
    
    Args:
        request: FastAPI request object
        exc: Application exception

    Returns:
        JSON response with error details
    """
    settings = _get_settings()
    
    # Include traceback in development mode
    detail = exc.detail
    if settings.API.DEBUG and not detail:
        detail = {"traceback": traceback.format_exc()}
    
    # Create error response
    error_response = ErrorResponse(
        status=exc.status_code.value,
        code=exc.status_code.name,
        message=exc.message,
        detail=detail,
        path=request.url.path,
    )
    
    # Return JSON response with appropriate status code and headers
    return JSONResponse(
        status_code=exc.status_code.value,
        content=jsonable_encoder(error_response.model_dump()),
        headers=exc.headers,
    )


def _handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI's HTTPException.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception

    Returns:
        JSON response with error details
    """
    status_code = exc.status_code
    try:
        http_status = HTTPStatus(status_code)
        error_code = http_status.name
    except ValueError:
        error_code = f"HTTP_{status_code}"
    
    # Create error response
    error_response = ErrorResponse(
        status=status_code,
        code=error_code,
        message=exc.detail,
        path=request.url.path,
    )
    
    # Return JSON response with appropriate status code and headers
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(error_response.model_dump()),
        headers=exc.headers,
    )


def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle FastAPI's RequestValidationError.
    
    This handler formats Pydantic validation errors in a consistent way.
    
    Args:
        request: FastAPI request object
        exc: Validation exception

    Returns:
        JSON response with validation error details
    """
    # Format validation errors
    errors = []
    for error in exc.errors():
        error_dict = {
            "loc": " -> ".join([str(loc) for loc in error["loc"]]),
            "msg": error["msg"],
            "type": error["type"],
        }
        errors.append(error_dict)
    
    # Create error response
    error_response = ErrorResponse(
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=HTTPStatus.UNPROCESSABLE_ENTITY.name,
        message="Request validation error",
        detail=errors,
        path=request.url.path,
    )
    
    # Return JSON response with appropriate status code
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response.model_dump()),
    )


def _handle_python_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unhandled Python exceptions.
    
    This is a catch-all handler for exceptions that don't have specific handlers.
    
    Args:
        request: FastAPI request object
        exc: Python exception

    Returns:
        JSON response with error details
    """
    settings = _get_settings()
    
    # Determine error details
    detail = None
    if settings.API.DEBUG:
        detail = {
            "type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        }
    
    # Create error response
    error_response = ErrorResponse(
        status=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        code=HTTPStatus.INTERNAL_SERVER_ERROR.name,
        message="Internal server error",
        detail=detail,
        path=request.url.path,
    )
    
    # Return JSON response with 500 status code
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        content=jsonable_encoder(error_response.model_dump()),
    )


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
    # Register handlers for FastAPI's built-in exceptions
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    
    # Register handlers for custom application exceptions
    app.add_exception_handler(AppError, _handle_app_error)
    
    # Add handler for all other Python exceptions
    app.add_exception_handler(Exception, _handle_python_exception)


def get_error_responses(
    *exception_classes: Type[Exception]
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
            ValidationError,
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
            "description": getattr(exc_class, "__doc__", "").strip() or exc_class.__name__,
        }
    
    return responses