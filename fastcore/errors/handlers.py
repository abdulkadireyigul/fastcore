"""
Exception handlers for FastAPI applications.

This module provides exception handlers that convert application exceptions
into standardized API responses using the schemas module.
"""

import traceback
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from fastcore.errors.exceptions import AppError
from fastcore.logging import Logger, ensure_logger
from fastcore.schemas import ErrorInfo, ErrorResponse
from fastcore.schemas.metadata import ResponseMetadata


def create_error_response(
    status_code: int,
    message: str,
    code: str = "ERROR",
    errors: Optional[List[ErrorInfo]] = None,
    metadata: Optional[ResponseMetadata] = None,
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        message: Error message
        code: Error code identifier
        errors: Detailed error information list
        metadata: Additional metadata for the response

    Returns:
        Standardized error response
    """
    return ErrorResponse(
        success=False,
        message=message,
        errors=errors or [ErrorInfo(code=code, message=message)],
        metadata=metadata or ResponseMetadata(),
    )


def _create_validation_errors(
    errors_data: List[Dict[str, Any]], exclude_body: bool = False
) -> List[ErrorInfo]:
    """
    Create a list of ErrorInfo objects from validation errors data.

    Args:
        errors_data: List of error dictionaries
        exclude_body: Whether to exclude 'body' from location paths

    Returns:
        List of ErrorInfo objects
    """
    errors = []

    for error in errors_data:
        # Extract field path and format it
        loc = error.get("loc", [])

        if exclude_body:
            field_path = ".".join([str(item) for item in loc if item != "body"])
        else:
            field_path = ".".join([str(item) for item in loc])

        # Create error info
        error_info = ErrorInfo(
            code="VALIDATION_ERROR",
            message=error.get("msg", "Validation error"),
            field=field_path,
        )
        errors.append(error_info)

    return errors


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Handler for AppError and its subclasses.

    Args:
        request: FastAPI request
        exc: AppError instance

    Returns:
        JSON response with error details
    """
    # Extract error details
    errors = [ErrorInfo(code=exc.code, message=exc.message)]

    # Add field validation errors if available
    if hasattr(exc, "fields") and exc.fields:
        errors = []
        for field_error in exc.fields:
            field_name = field_error.get("field", "")
            error = ErrorInfo(
                code=field_error.get("code", exc.code),
                message=field_error.get("message", exc.message),
                field=field_name,
            )
            errors.append(error)

    response = create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        errors=errors,
        metadata=ResponseMetadata(),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(response),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for FastAPI's RequestValidationError.

    Args:
        request: FastAPI request
        exc: ValidationError instance

    Returns:
        JSON response with validation error details
    """
    errors = _create_validation_errors(exc.errors(), exclude_body=True)

    response = create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation error",
        code="VALIDATION_ERROR",
        errors=errors,
        metadata=ResponseMetadata(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(response),
    )


async def pydantic_validation_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """
    Handler for Pydantic's ValidationError.

    Args:
        request: FastAPI request
        exc: Pydantic ValidationError instance

    Returns:
        JSON response with validation error details
    """
    errors = _create_validation_errors(exc.errors(), exclude_body=False)

    response = create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Data validation error",
        code="VALIDATION_ERROR",
        errors=errors,
        metadata=ResponseMetadata(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(response),
    )


async def http_exception_handler(
    request: Request, exc: Exception, logger: Optional[Logger] = None
) -> JSONResponse:
    """
    Generic exception handler for unhandled exceptions.

    Args:
        request: FastAPI request
        exc: Unhandled exception
        logger: Optional logger to use instead of default logging

    Returns:
        JSON response with generic error message
    """
    # ensure_logger kullanarak tutarlı logging
    log = ensure_logger(logger, __name__)
    log.error(f"Unhandled exception: {str(exc)}")
    log.error(traceback.format_exc())

    response = create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
        code="INTERNAL_ERROR",
        metadata=ResponseMetadata(),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(response),
    )


def register_exception_handlers(
    app: FastAPI, logger: Optional[Logger] = None, debug: bool = False
) -> None:
    """
    Register all exception handlers with a FastAPI application.

    Args:
        app: FastAPI application instance
        logger: Optional logger for logging exceptions
        debug: Whether to include detailed debug info in responses.
               Currently reserved for future use.
    """
    # Register the base AppError handler - this will automatically handle all subclasses
    app.exception_handler(AppError)(app_error_handler)

    # Framework exceptions
    app.exception_handler(RequestValidationError)(validation_exception_handler)
    app.exception_handler(PydanticValidationError)(pydantic_validation_handler)

    # Global exception handler for unhandled exceptions
    # Pass the logger to the exception handler using partial function
    from functools import partial

    global_handler = partial(http_exception_handler, logger=logger)
    app.exception_handler(Exception)(global_handler)

    # Debug mode can be used in the future to add additional information
    # to error responses or customize error handling behavior
    if debug:
        # Reserved for future implementation
        pass
