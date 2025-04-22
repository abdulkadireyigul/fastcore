"""
FastAPI application factory module.

This module provides a function to configure FastAPI applications
with standardized settings and error handling.
"""

from typing import Optional

from fastapi import FastAPI

from fastcore.cache import setup_cache
from fastcore.config import BaseAppSettings, get_settings
from fastcore.db import setup_db
from fastcore.errors import setup_errors
from fastcore.logging.manager import ensure_logger
from fastcore.middleware import setup_middlewares
from fastcore.security import setup_security


def configure_app(app: FastAPI, settings: Optional[BaseAppSettings] = None) -> None:
    """
    Configure a FastAPI application with standard settings and error handling.

    The application instance should be created by the main application and passed
    to this function for configuration.

    Args:
        app: The FastAPI application to configure
        settings: Optional application settings, if not provided will be loaded
                 from environment
    """
    # Get or use provided settings
    app_settings = settings or get_settings()

    # Get logger for error handling
    # logger = get_logger(__name__, app_settings)
    logger = ensure_logger(None, __name__, app_settings)

    # Configure title and version if not already set
    if not app.title:
        app.title = app_settings.APP_NAME
    if not app.version:
        app.version = app_settings.VERSION

    # Set debug mode
    app.debug = app_settings.DEBUG

    # Configure error handling (required)
    setup_errors(app, app_settings, logger)
    # Configure caching (optional)
    setup_cache(app, app_settings, logger)
    # Configure database
    setup_db(app, app_settings, logger)
    # Configure security
    setup_security(app, app_settings, logger)
    # Configure middleware (CORS, rate limiting, etc.)
    setup_middlewares(app, app_settings, logger)
