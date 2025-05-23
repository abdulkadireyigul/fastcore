"""
CORS middleware integration for FastAPI applications.

Adds CORS middleware to the application using options from settings.

Limitations:
- Only global CORS configuration is supported (no per-route config)
- Options must be provided as a dictionary in settings.MIDDLEWARE_CORS_OPTIONS
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastcore.config.base import BaseAppSettings
from fastcore.logging.manager import Logger


def add_cors_middleware(app: FastAPI, settings: BaseAppSettings, logger: Logger):
    """
    Adds CORS middleware to the application. Options are loaded from config.

    Features:
    - Configurable via settings.MIDDLEWARE_CORS_OPTIONS (dict)
    - Sensible defaults if not provided

    Limitations:
    - Only global CORS configuration is supported (no per-route config)
    - Options must be provided as a dictionary in settings.MIDDLEWARE_CORS_OPTIONS
    """
    cors_options = getattr(
        settings,
        "MIDDLEWARE_CORS_OPTIONS",
        {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        },
    )
    logger.info(f"Configuring CORS middleware with options: {cors_options}")
    app.add_middleware(CORSMiddleware, **cors_options)
    logger.debug("CORS middleware added to FastAPI application.")
