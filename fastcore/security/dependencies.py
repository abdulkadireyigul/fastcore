"""
Security dependencies for FastAPI.

This module provides dependency functions for FastAPI applications
to handle authentication and secure routes.
"""

from typing import Any, Callable, Dict, Optional, TypeVar

from fastapi import Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.config import get_settings
from fastcore.db import get_db
from fastcore.security.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.manager import get_security_status
from fastcore.security.models import TokenType
from fastcore.security.tokens import (
    create_token_pair,
    refresh_access_token,
    revoke_all_user_tokens,
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
    auth_handler: UserAuthentication[UserT],
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
            # Get the user using the provided authentication handler
            user = await auth_handler.get_user_by_id(user_id)

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


async def get_refresh_token_from_cookie(
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token")
) -> str:
    """
    Extract refresh token from HTTP-only cookie.

    Args:
        refresh_token: The refresh token extracted from cookie

    Returns:
        The refresh token

    Raises:
        HTTPException: If no refresh token is found in cookies
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found in cookies",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return refresh_token


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


async def logout_all_devices(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
    response: Response = None,
) -> Dict[str, str]:
    """
    Revoke all tokens for the current user across all devices.

    This dependency is useful for security-sensitive operations like
    password changes or when suspicious activity is detected.

    Args:
        token: The current access token
        session: Database session for token operations
        response: FastAPI response object for cookie operations

    Returns:
        A success message
    """
    try:
        # First extract token data to get the user ID
        token_data = await validate_token(token, session, TokenType.ACCESS)
        user_id = token_data.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token content",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Revoke all tokens for this user
        await revoke_all_user_tokens(user_id, session)

        # Clear refresh token cookie if response object is provided
        if response:
            response.delete_cookie(
                key="refresh_token", httponly=True, secure=True, samesite="strict"
            )

        return {"message": "Successfully logged out from all devices"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout from all devices failed: {str(e)}",
        )


async def rotate_tokens(
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    session: AsyncSession = Depends(get_db),
    response: Response = None,
) -> Dict[str, str]:
    """
    Rotate both access and refresh tokens, enhancing security through regular token rotation.

    This dependency invalidates the current refresh token and issues a new token pair.
    This helps mitigate the risk of token theft by regularly changing tokens.

    Args:
        refresh_token: The current refresh token
        session: Database session for token operations
        response: Response object for setting the new refresh token cookie

    Returns:
        A dictionary with the new access token

    Raises:
        HTTPException: If token refresh fails
    """
    try:
        # Validate the refresh token
        token_data = await validate_token(refresh_token, session, TokenType.REFRESH)
        user_id = token_data.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token content",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Revoke the current refresh token
        await revoke_token(refresh_token, session)

        # Create new token pair
        token_pair = await create_token_pair({"sub": user_id}, session)

        # Set the new refresh token in an HTTP-only cookie
        if response:
            settings = get_settings()
            response.set_cookie(
                key="refresh_token",
                value=token_pair["refresh_token"],
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                path="/auth",  # Restrict cookie to auth endpoints
            )

        # Return only the access token in the response
        return {"access_token": token_pair["access_token"], "token_type": "bearer"}
    except (InvalidTokenError, ExpiredTokenError, RevokedTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e), "details": getattr(e, "details", {})},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token rotation failed: {str(e)}",
        )


async def verify_token_audience(
    token_data: Dict[str, Any] = Depends(get_token_data),
    expected_audiences: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Verify that a token has the appropriate audience claim.

    This is useful when different parts of your system need to
    ensure tokens were issued specifically for them.

    Args:
        token_data: The validated token data
        expected_audiences: List of accepted audiences

    Returns:
        The original token data if valid

    Raises:
        HTTPException: If token audience validation fails
    """
    if not expected_audiences:
        return token_data

    token_audience = token_data.get("aud")

    # Handle the case where the token audience might be a string or a list
    if isinstance(token_audience, str):
        token_audiences = [token_audience]
    else:
        token_audiences = token_audience or []

    # Check if any of the token audiences match the expected audiences
    if not any(aud in expected_audiences for aud in token_audiences):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Token was not issued for this audience",
                "details": {
                    "expected_audiences": expected_audiences,
                    "token_audiences": token_audiences,
                },
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data
