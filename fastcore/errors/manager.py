"""
Error management functionality for FastAPI applications.

This module provides the main entry point for configuring error handling
in a FastAPI application, including exception handler registration.
"""

from typing import Optional

from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings
from fastcore.errors.handlers import register_exception_handlers
from fastcore.logging import ensure_logger


def setup_errors(
    app: FastAPI,
    settings: Optional[BaseAppSettings] = None,
    logger: Optional[object] = None,
) -> None:
    """
    Configure error handling for a FastAPI application.

    This function sets up standardized error handling by registering exception handlers
    that convert exceptions into consistent API responses.

    Args:
        app: FastAPI application instance
        settings: Optional application settings
        logger: Optional logger for logging exceptions
    """
    # ensure_logger kullanarak tutarlı logging
    log = ensure_logger(logger, __name__, settings)

    # Safely check debug mode
    debug = False
    if settings and hasattr(settings, "DEBUG"):
        debug = bool(settings.DEBUG)

    # Register all exception handlers
    register_exception_handlers(app, logger=log, debug=debug)
