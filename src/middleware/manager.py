from typing import Optional

from fastapi import FastAPI

from src.config.base import BaseAppSettings
from src.logging.manager import Logger, ensure_logger

from .cors import add_cors_middleware
from .rate_limiting import add_rate_limiting_middleware


def setup_middlewares(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Sets up all middlewares for the application. Extend here for lifecycle management if needed.
    """
    log = ensure_logger(logger, __name__, settings)

    add_cors_middleware(app, settings, log)
    add_rate_limiting_middleware(app, settings, log)
