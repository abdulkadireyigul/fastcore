"""
Security module manager.

This module provides a setup function for initializing the security module
and integrating it with a FastAPI application.
"""

from typing import Optional

from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings
from fastcore.logging import Logger, ensure_logger

# Configure logger
logger = ensure_logger(None, __name__)

# Global security state flag
security_initialized = False


def setup_security(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Configure security features for a FastAPI application.

    This function initializes the security module for a FastAPI application,
    setting up token management and database tables.

    Args:
        app: The FastAPI application to configure
        settings: Application settings
        logger: Optional logger instance
    """
    global security_initialized
    log = ensure_logger(logger, __name__, settings)

    async def on_startup():
        global security_initialized
        log.info("Initializing security module")

        # Log security configuration
        log.info(
            f"JWT token lifetime: {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} minutes"
        )
        log.info(f"JWT algorithm: {settings.JWT_ALGORITHM}")
        log.info(
            f"JWT refresh token lifetime: {settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS} days"
        )

        security_initialized = True
        log.info("Security module initialized")

    async def on_shutdown():
        global security_initialized
        log.info("Shutting down security module")
        security_initialized = False

    app.add_event_handler("startup", on_startup)
    app.add_event_handler("shutdown", on_shutdown)


def get_security_status() -> bool:
    """
    FastAPI dependency for checking security module initialization status.

    Returns:
        bool: Whether the security module is initialized

    Raises:
        RuntimeError: If the security module is not initialized
    """
    if not security_initialized:
        raise RuntimeError("Security module not initialized")
    return security_initialized
