"""
Security setup integration for FastAPI applications.

This module provides functions to integrate security features with FastAPI applications.
"""

import logging
from typing import Dict, List, Optional, Union

from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings
from fastcore.db import get_db

from .authorization.permissions import (
    Permission as SecurityPermission,  # Rename to avoid confusion with DB model
)


async def init_role_db(
    app: FastAPI, default_roles: Dict[str, List[Union[str, SecurityPermission]]]
) -> None:
    """
    Initialize roles in the database when the application starts.

    Args:
        app: FastAPI application instance
        default_roles: Dictionary mapping role names to permission lists
    """
    # Get a db session directly
    db_dependency = get_db()
    db = await db_dependency.__anext__()

    try:
        # Add roles directly to database
        from .authorization.permissions import role_manager

        for role_name, permissions in default_roles.items():
            try:
                # Check if role exists first
                role = await role_manager.get_role(db, role_name)
                if not role:
                    # Create role with permissions
                    await role_manager.add_role(db, role_name, permissions)
                else:
                    # Add permissions to existing role
                    for perm in permissions:
                        await role_manager.add_permission_to_role(db, role_name, perm)
            except Exception as e:
                app.state.logger.error(f"Error setting up role {role_name}: {str(e)}")

    finally:
        try:
            await db_dependency.__aexit__(None, None, None)
        except Exception:
            pass


def setup_security(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[logging.Logger] = None,
    default_roles: Optional[Dict[str, List[Union[str, SecurityPermission]]]] = None,
) -> None:
    """
    Set up security features for a FastAPI application.

    This function configures security settings and hooks for a FastAPI application.
    It doesn't add any routes or middleware by default, but can initialize the role
    manager with default roles if provided.

    Args:
        app: The FastAPI application to configure
        settings: Application settings
        logger: Optional logger instance
        default_roles: Optional dictionary mapping role names to permission lists
                      Example: {"admin": ["*:*"], "user": ["items:read"]}
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

    # Setup default roles in DB if provided
    if default_roles:
        # Register startup event to initialize roles in DB
        @app.on_event("startup")
        async def init_roles():
            log.info(f"Initializing default roles: {', '.join(default_roles.keys())}")
            await init_role_db(app, default_roles)
