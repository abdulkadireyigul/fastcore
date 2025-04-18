"""
Security setup integration for FastAPI applications.

This module provides functions to integrate security features with FastAPI applications.
"""

import logging
from typing import Optional

from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings

# from fastcore.db import get_db
# from .authorization.permissions import (
#     Permission as SecurityPermission,  # Rename to avoid confusion with DB model
# )


# async def init_role_db(
#     app: FastAPI, default_roles: Dict[str, List[Union[str, SecurityPermission]]]
# ) -> None:
#     """
#     Initialize roles in the database when the application starts.
#     This functionality is currently disabled.
#     """
#     pass  # Placeholder for future implementation


def setup_security(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[logging.Logger] = None,
    # default_roles: Optional[Dict[str, List[Union[str, str]]]] = None,
) -> None:
    """
    Set up security features for a FastAPI application.

    This function configures security settings and hooks for a FastAPI application.
    It only sets up JWT token validation, role-based authorization is disabled.

    Args:
        app: The FastAPI application to configure
        settings: Application settings
        logger: Optional logger instance
        default_roles: Optional dictionary mapping role names to permission lists
                      (Currently not used as role-based auth is disabled)
    """
    log = logger or logging.getLogger(__name__)

    # Log security configuration
    log.info(
        f"Security initialized with algorithm {settings.JWT_ALGORITHM}, "
        f"token expiry {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} minutes"
    )

    # Store security settings in app state for access in middleware/dependencies
    app.state.security_settings = {
        "algorithm": settings.JWT_ALGORITHM,
        "token_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    }

    # if default_roles:
    #     @app.on_event("startup")
    #     async def init_roles():
    #         log.info(f"Initializing default roles: {', '.join(default_roles.keys())}")
    #         await init_role_db(app, default_roles)
