"""
Security dependencies for FastAPI.

This module provides dependency functions for FastAPI applications
to handle authentication and secure routes.
"""

from typing import Any, Callable, Dict, Optional, TypeVar

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_db
from fastcore.security.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.manager import get_security_status
from fastcore.security.tokens.models import TokenType
from fastcore.security.tokens.service import (
    refresh_access_token,
    revoke_token,
    validate_token,
)
from fastcore.security.users import UserAuthentication

# OAuth2 password bearer scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Generic type for user models
UserT = TypeVar("UserT")


async def get_token_data(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
    _: bool = Depends(get_security_status),
    token_type: Optional[TokenType] = TokenType.ACCESS,
) -> Dict[str, Any]:
    """
    Validate the access token and return its data.

    This dependency extracts and validates the JWT token
    from the request, including stateful validation.

    Args:
        token: The JWT token extracted from the Authorization header
        session: Database session for stateful validation
        _: Security status check (ensures security is initialized)
        token_type: The expected token type (default: access)

    Returns:
        The decoded token payload if valid

    Raises:
        HTTPException: With appropriate status code if token is invalid
    """
    try:
        return await validate_token(token, session, token_type)
    except ExpiredTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Token has expired",
                "details": getattr(e, "details", {}),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except RevokedTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Token has been revoked",
                "details": getattr(e, "details", {}),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e), "details": getattr(e, "details", {})},
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_dependency(
    # auth_handler: UserAuthentication[UserT],
    auth_handler_dependency: Callable = Depends(),
) -> Callable[[Dict[str, Any]], UserT]:
    """
    Create a dependency function for getting the current authenticated user.

    This factory function creates a dependency that works with any user model
    through the provided authentication handler.

    Args:
        auth_handler: Implementation of UserAuthentication for the app's user model

    Returns:
        A dependency function that returns the current authenticated user
    """

    async def current_user_dependency(
        token_data: Dict[str, Any] = Depends(get_token_data),
        auth_handler: UserAuthentication[UserT] = Depends(auth_handler_dependency),
    ) -> UserT:
        """
        Get the current authenticated user from the token.

        Args:
            token_data: The validated token data

        Returns:
            The user object

        Raises:
            HTTPException: If no valid user found
        """
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token content",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            if auth_handler is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication handler is not initialized",
                )

            # Get the user using the provided authentication handler
            user = await auth_handler.get_user_by_id(int(user_id))

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate user: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return current_user_dependency


async def get_refresh_token_data(
    token: str,
    session: AsyncSession = Depends(get_db),
    _: bool = Depends(get_security_status),
) -> Dict[str, Any]:
    """
    Validate a refresh token.

    Args:
        token: The refresh token to validate
        session: Database session for token operations
        _: Security status check (ensures security is initialized)

    Returns:
        The decoded token payload if valid

    Raises:
        HTTPException: If the token is invalid
    """
    try:
        return await validate_token(token, session, TokenType.REFRESH)
    except ExpiredTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Refresh token has expired",
                "details": getattr(e, "details", {}),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except RevokedTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Refresh token has been revoked",
                "details": getattr(e, "details", {}),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e), "details": getattr(e, "details", {})},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def refresh_token(
    token: str,
    session: AsyncSession = Depends(get_db),
) -> str:
    """
    Create a new access token using a valid refresh token.

    Args:
        token: The refresh token to refresh
        session: Database session for token operations

    Returns:
        A new access token
    """
    try:
        # Validate and refresh the token
        return await refresh_access_token(token, session)
    except (InvalidTokenError, ExpiredTokenError, RevokedTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e), "details": getattr(e, "details", {})},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def logout_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
    response: Response = None,
) -> Dict[str, str]:
    """
    Revoke the current access token and clear any refresh token cookies.

    Args:
        token: The access token to revoke
        session: Database session for token operations
        response: FastAPI response object for cookie operations

    Returns:
        A success message
    """
    try:
        # Revoke the current token
        await revoke_token(token, session)

        # Clear refresh token cookie if response object is provided
        if response:
            response.delete_cookie(
                key="refresh_token", httponly=True, secure=True, samesite="strict"
            )

        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )
