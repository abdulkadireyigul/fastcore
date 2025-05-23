from typing import Optional

from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings
from fastcore.logging.manager import Logger, ensure_logger

from .cors import add_cors_middleware
from .rate_limiting import add_rate_limiting_middleware


def setup_middlewares(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Sets up all middlewares for the application.

    Features:
    - Adds CORS middleware (configurable via settings.MIDDLEWARE_CORS_OPTIONS)
    - Adds rate limiting middleware (memory or Redis backend)

    Limitations:
    - Only CORS and rate limiting middleware are included by default
    - No request timing middleware is implemented
    - No per-route or user-based rate limiting
    - Middleware is set up at startup, not dynamically per request
    - Advanced CORS and rate limiting features (e.g., per-route config, custom backends) are not included
    """
    log = ensure_logger(logger, __name__, settings)

    add_cors_middleware(app, settings, log)
    add_rate_limiting_middleware(app, settings, log)
