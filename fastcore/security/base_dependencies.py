"""
Base Security Dependencies Module.

This module defines the `BaseSecurityDependencies` class, designed to be 
agnostic of the underlying token implementation and user authentication model.
It uses Generic types to support different Authentication Handlers (Legacy vs UUID).
"""

import os
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_db
from fastcore.errors.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.manager import get_security_status
from fastcore.security.tokens.types import TokenType

# Generic type for user models (e.g. User, UUIDUser)
UserT = TypeVar("UserT")

# Generic type for Auth Handlers (e.g. UserAuthentication, UUIDUserAuthentication)
# We bind it to 'Any' or 'UserAuthentication' to allow flexibility but ensure basic compatibility.
AuthHandlerT = TypeVar("AuthHandlerT", bound=Any)


class BaseSecurityDependencies(Generic[UserT, AuthHandlerT]):
    """
    A base class for handling security dependencies in FastAPI applications.

    This class implements the 'Template Method' and 'Dependency Injection' patterns.
    It is Generic over the User type and the Authentication Handler type, allowing
    it to adapt to both Legacy (Integer-based) and UUID-based systems cleanly.

    Attributes:
        service_module: The module containing token service functions.
        id_converter: A callable to convert the user ID from the token.
        oauth2_scheme: The FastAPI OAuth2PasswordBearer instance.
    """

    def __init__(
        self,
        service_module: Any,
        id_converter: Callable[[Any], Any] = lambda x: x,
        token_url: str = "login",
    ):
        """
        Initialize the security dependencies.

        Args:
            service_module: Module providing `validate_token`, `refresh_access_token`, etc.
            id_converter: Function to convert the subject ID (e.g. int vs str).
            token_url: The OAuth2 login URL.
        """
        self.service = service_module
        self.id_converter = id_converter
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_url)

    async def get_token_data(
        self,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="login")),
        session: AsyncSession = Depends(get_db),
        _: bool = Depends(get_security_status),
        token_type: Optional[TokenType] = TokenType.ACCESS,
    ) -> Dict[str, Any]:
        """
        Validate the access token and return its data.

        Features:
        - Extracts and validates JWT token from the request
        - Supports stateful validation

        Limitations:
        - Only password-based JWT authentication is included by default
        - No OAuth2/social login/multi-factor authentication
        - No advanced RBAC or permission system
        - No API key support

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
            return await self.service.validate_token(token, session, token_type)
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
        self,
        auth_handler_dependency: Callable[..., AuthHandlerT] = Depends(),
    ) -> Callable[..., Awaitable[UserT]]:
        """
        Create a dependency function for getting the current authenticated user.

        This factory function creates a dependency that works with any user model
        through the provided authentication handler.

        Args:
            auth_handler_dependency: Dependency that provides UserAuthentication implementation

        Returns:
            A dependency function that returns the current authenticated user
        """

        async def current_user_dependency(
            token_data: Dict[str, Any] = Depends(self.get_token_data),
            auth_handler: AuthHandlerT = Depends(auth_handler_dependency),
        ) -> UserT:
            """
            Get the current authenticated user from the token.

            Args:
                token_data: The validated token data
                auth_handler: Authentication handler for user operations

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

                # Convert ID (str -> int or str -> str)
                converted_id = self.id_converter(user_id)

                # Duck Typing: We assume the handler has get_user_by_id
                # Get the user using the provided authentication handler
                user = await auth_handler.get_user_by_id(converted_id)

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
        self,
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
            return await self.service.validate_token(token, session, TokenType.REFRESH)
        except (ExpiredTokenError, RevokedTokenError, InvalidTokenError) as e:
            if isinstance(e, ExpiredTokenError):
                msg = "Refresh token has expired"
            elif isinstance(e, RevokedTokenError):
                msg = "Refresh token has been revoked"
            else:
                msg = str(e)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": msg, "details": getattr(e, "details", {})},
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def refresh_token(
        self,
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
            return await self.service.refresh_access_token(token, session)
        except (InvalidTokenError, ExpiredTokenError, RevokedTokenError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": str(e), "details": getattr(e, "details", {})},
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def logout_user(
        self,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="login")),
        session: AsyncSession = Depends(get_db),
        response: Optional[Response] = None,
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
            await self.service.revoke_token(token, session)

            # Clear refresh and access token cookies if response object is provided
            if response:
                await self.remove_auth_cookies(response)

            return {"message": "Successfully logged out"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Logout failed: {str(e)}",
            )

    # --- Cookie Based Methods ---

    async def get_token_data_from_cookie(
        self,
        request: Request,
        session: AsyncSession = Depends(get_db),
        _: bool = Depends(get_security_status),
        token_type: Optional[TokenType] = TokenType.ACCESS,
    ) -> Dict[str, Any]:
        """
        Validate the token from an HTTP-only cookie and return its data.

        This function is similar to `get_token_data` but extracts the token from
        the 'access_token' cookie rather than the Authorization header.

        Args:
            request: The FastAPI request object containing the cookies.
            session: Database session for stateful validation.
            _: Security status check (ensures security is initialized).
            token_type: The expected token type (default: access).

        Returns:
            The decoded token payload if valid.

        Raises:
            HTTPException: With status 401 if no token is found or if the token is invalid,
                        expired, or revoked.
        """
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication token found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await self.get_token_data(token, session, _, token_type)

    def get_current_user_from_cookie_dependency(
        self,
        auth_handler_dependency: Callable[..., AuthHandlerT] = Depends(),
    ) -> Callable[..., Awaitable[UserT]]:
        """
        Create a dependency function to get the current authenticated user from a cookie.

        This factory function wraps `get_token_data_from_cookie` and `get_user_by_id`
        to provide a dependency for securing endpoints that use cookie-based authentication.

        Args:
            auth_handler_dependency: The dependency that provides the UserAuthentication handler.

        Returns:
            A dependency function that returns the current authenticated user object.
        """

        async def current_user_from_cookie_dependency(
            token_data: Dict[str, Any] = Depends(self.get_token_data_from_cookie),
            auth_handler: AuthHandlerT = Depends(auth_handler_dependency),
        ) -> UserT:
            """
            Get the current authenticated user from the token in a cookie.
            """
            # The logic here is identical to the original function
            user_id = token_data.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token content",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            try:
                converted_id = self.id_converter(user_id)
                user = await auth_handler.get_user_by_id(converted_id)
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

        return current_user_from_cookie_dependency

    async def logout_user_cookie(
        self,
        request: Request,
        session: AsyncSession = Depends(get_db),
        response: Optional[Response] = None,
    ) -> Dict[str, str]:
        """
        Revoke the current access token from a cookie and clear authentication cookies.

        This function retrieves the access token from the 'access_token' cookie,
        revokes it, and then deletes both access and refresh token cookies from
        the client's browser.

        Args:
            request: The FastAPI request object containing the cookies.
            session: Database session for token operations.
            response: FastAPI response object for cookie operations.

        Returns:
            A success message.

        Raises:
            HTTPException: With status 401 if no token is found in the cookie.
            HTTPException: With status 500 if the logout operation fails.
        """
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication token found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await self.logout_user(token, session, response)

    # --- Static Utilities ---

    @staticmethod
    def set_auth_cookies(
        response: Response,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> None:
        """
        Set authentication cookies on the response with secure and HttpOnly flags.

        This utility function is designed to be called from login and refresh endpoints
        to securely store tokens on the client side.

        Args:
            response: The FastAPI response object to set the cookies on.
            access_token: The JWT access token string.
            refresh_token: The optional JWT refresh token string.
        """
        # Determine if the environment is development to set the secure flag
        is_dev_env = os.getenv("APP_ENV") == "development"
        secure = not is_dev_env

        # Get expiration times from environment variables, with a fallback to defaults
        access_token_expires_minutes = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        refresh_token_expires_days = int(
            os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
        )

        # Calculate max_age in seconds
        max_age_access = access_token_expires_minutes * 60
        max_age_refresh = refresh_token_expires_days * 86400

        if access_token:
            response.set_cookie(
                key="access_token",
                value=access_token,
                max_age=max_age_access,
                httponly=True,
                secure=secure,
                samesite="none" if secure else "strict",
            )

        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                max_age=max_age_refresh,
                httponly=True,
                secure=secure,
                samesite="none" if secure else "strict",
            )

    async def remove_auth_cookies(
        self, response: Response | None = None
    ) -> Dict[str, str]:
        """
        Remove the current access token and refresh token cookies.

        Args:
            response: FastAPI response object for cookie operations

        Returns:
            A success message
        """
        try:
            # Determine if the environment is development to set the secure flag
            is_dev_env = os.getenv("APP_ENV") == "development"
            secure = not is_dev_env

            # Clear refresh and access token cookies if response object is provided
            if response:
                response.delete_cookie(
                    key="access_token",
                    httponly=True,
                    secure=secure,
                    samesite="none" if secure else "strict",
                )
                response.delete_cookie(
                    key="refresh_token",
                    httponly=True,
                    secure=secure,
                    samesite="none" if secure else "strict",
                )

            return {"message": "Successfully removed the auth cookies"}
        except Exception:
            return {"message": "Failed to remove the auth cookies"}


# Exports
set_auth_cookies = BaseSecurityDependencies.set_auth_cookies
remove_auth_cookies = BaseSecurityDependencies.remove_auth_cookies
