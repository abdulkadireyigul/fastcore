"""
Security dependencies for FastAPI applications.

This module provides dependency functions for integrating authentication and
authorization into FastAPI route handlers.
"""

from typing import Any, Callable, Dict, List, Optional, Set, Union, cast

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import BaseModel, ValidationError

from fastcore.errors.exceptions import AppError, AuthenticationError, AuthorizationError
from fastcore.logging import get_logger
from fastcore.security.auth import JWTAuth, JWTPayload

# Get a logger for this module
logger = get_logger(__name__)


class User(BaseModel):
    """
    Base user model for authentication.

    This class represents the basic user information needed for
    authentication. Applications should extend this with additional
    fields as needed.
    """

    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    roles: List[str] = []
    permissions: List[str] = []


# Placeholder for the JWT authentication handler
# This should be configured and instantiated when setting up the application
_jwt_auth: Optional[JWTAuth] = None

# OAuth2 password bearer scheme with support for scopes
_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={
        "users:read": "Read user information",
        "users:write": "Create or update user information",
        "admin": "Admin access",
    },
)


def configure_jwt_auth(jwt_auth: JWTAuth) -> None:
    """
    Configure the JWT authentication handler.

    This function should be called during application startup
    to configure the JWT authentication handler.

    Args:
        jwt_auth: The JWT authentication handler to use
    """
    global _jwt_auth
    _jwt_auth = jwt_auth

    # Update the tokenUrl in OAuth2 scheme
    global _oauth2_scheme
    if hasattr(_oauth2_scheme, "tokenUrl"):
        _oauth2_scheme.tokenUrl = jwt_auth.config.TOKEN_URL


def get_current_token(
    security_scopes: SecurityScopes,
    token: str = Depends(_oauth2_scheme),
) -> JWTPayload:
    """
    Extract and validate the JWT token from the request.

    This dependency extracts and validates the JWT token from the request,
    checking that it has the required scopes.

    Args:
        security_scopes: The security scopes required for this endpoint
        token: The JWT token from the Authorization header

    Returns:
        The decoded JWT payload

    Raises:
        HTTPException: If the token is invalid or missing required scopes
    """
    if _jwt_auth is None:
        logger.error("JWT authentication handler not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: authentication not configured",
        )

    try:
        # Decode and validate the token
        payload = _jwt_auth.decode_token(token)

        # Check scopes if required
        if security_scopes.scopes:
            # Convert space-separated scope string to a set
            token_scopes = set(payload.scope.split() if payload.scope else [])
            required_scopes = set(security_scopes.scopes)

            # Check if the token has all required scopes
            if not required_scopes.issubset(token_scopes):
                raise AuthorizationError(
                    f"Not enough permissions. Required scopes: {', '.join(required_scopes)}",
                    headers={
                        "WWW-Authenticate": f"Bearer scope=\"{' '.join(security_scopes.scopes)}\""
                    },
                )

        return payload

    except (ValidationError, AuthenticationError) as e:
        # Re-raise authentication errors with proper headers
        raise AuthenticationError(
            str(e),
            headers={
                "WWW-Authenticate": f"Bearer scope=\"{' '.join(security_scopes.scopes)}\""
            },
        )
    except AppError:
        # Pass through application errors
        raise


# User retrieval function type
# This function should be implemented by the application to retrieve a user from the database
UserRetriever = Callable[[str], User]
_user_retriever: Optional[UserRetriever] = None


def configure_user_retriever(retriever: UserRetriever) -> None:
    """
    Configure the user retrieval function.

    This function should be called during application startup
    to configure the function used to retrieve users from the database.

    Args:
        retriever: A function that takes a user ID and returns a User object
    """
    global _user_retriever
    _user_retriever = retriever


def get_current_user(
    token: JWTPayload = Security(get_current_token, scopes=[]),
) -> User:
    """
    Get the current authenticated user.

    This dependency extracts the user ID from the JWT token and
    retrieves the user from the database.

    Args:
        token: The decoded JWT payload from get_current_token

    Returns:
        The current authenticated user

    Raises:
        HTTPException: If the user could not be found
    """
    if _user_retriever is None:
        logger.error("User retriever not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: user retrieval not configured",
        )

    try:
        # Extract the user ID from the token
        user_id = token.sub

        # Retrieve the user from the database
        user = _user_retriever(user_id)

        # Add any roles or permissions from the token
        if token.role and token.role not in user.roles:
            user.roles.append(token.role)

        if token.permissions:
            for permission in token.permissions:
                if permission not in user.permissions:
                    user.permissions.append(permission)

        return user

    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


def get_current_active_user(
    current_user: User = Security(get_current_user),
) -> User:
    """
    Get the current active user.

    This dependency extends get_current_user to also check
    that the user is not disabled.

    Args:
        current_user: The current authenticated user from get_current_user

    Returns:
        The current active user

    Raises:
        HTTPException: If the user is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return current_user


def get_current_superuser(
    current_user: User = Security(get_current_active_user),
) -> User:
    """
    Get the current user and check if they are a superuser.

    This dependency extends get_current_active_user to also check
    that the user has the superuser role.

    Args:
        current_user: The current active user from get_current_active_user

    Returns:
        The current superuser

    Raises:
        HTTPException: If the user is not a superuser
    """
    if "superuser" not in current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )

    return current_user


def require_permissions(required_permissions: List[str]) -> Callable:
    """
    Create a dependency that requires specific permissions.

    This function creates a dependency that checks if the current user
    has all the required permissions.

    Args:
        required_permissions: The permissions required to access the endpoint

    Returns:
        A dependency function that checks permissions

    Example:
        ```python
        @app.get("/users/", dependencies=[Depends(require_permissions(["users:read"]))])
        def list_users():
            ...
        ```
    """

    def _check_permissions(
        current_user: User = Security(get_current_active_user),
    ) -> None:
        """Check if the user has all required permissions."""
        # Superusers have all permissions
        if "superuser" in current_user.roles or "admin" in current_user.roles:
            return

        # Check if the user has each required permission
        user_permissions = set(current_user.permissions)
        missing_permissions = []

        for permission in required_permissions:
            # Check direct permission
            if permission in user_permissions:
                continue

            # Check wildcard permissions
            if permission.count(":") == 1:
                resource, action = permission.split(":")
                if f"{resource}:*" in user_permissions:
                    continue

            # Check global wildcard
            if "*:*" in user_permissions:
                continue

            missing_permissions.append(permission)

        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {', '.join(missing_permissions)}",
            )

    # Return the dependency function
    return _check_permissions
