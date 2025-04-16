"""
Error management functionality for FastAPI applications.

This module provides the main entry point for configuring error handling
in a FastAPI application, including exception handler registration.
"""

import logging
from typing import Optional

from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings

from .handlers import register_exception_handlers


def setup_errors(
    app: FastAPI,
    settings: Optional[BaseAppSettings] = None,
    logger: Optional[logging.Logger] = None,
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
    # Safely check debug mode
    debug = False
    if settings and hasattr(settings, "DEBUG"):
        debug = bool(settings.DEBUG)

    # Register all exception handlers
    register_exception_handlers(app, logger=logger, debug=debug)
