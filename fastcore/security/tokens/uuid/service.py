"""
UUID Token Service Module.

This module provides the concrete implementation of the token service for
UUID-based systems. It acts as a specialized layer that configures the
generic business logic found in `BaseTokenService` to work specifically
with `UUIDToken` models and the `UUIDTokenRepository`.
"""

from datetime import timedelta
from typing import Any, Dict, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.security.tokens.base_service import BaseTokenService
from fastcore.security.tokens.models import TokenType

from .models import UUIDToken
from .repository import UUIDTokenRepository


class UUIDTokenService(BaseTokenService[UUIDToken]):
    """
    Service class for managing UUID-based tokens.

    This class inherits all core token logic (creation, validation, revocation)
    from `BaseTokenService` and wires it up with the UUID-specific repository
    and model.
    """

    def __init__(self):
        """
        Initialize the UUIDTokenService.

        Injects the `UUIDToken` model and `UUIDTokenRepository` into the base class.
        """
        super().__init__(model_cls=UUIDToken, repo_cls=UUIDTokenRepository)

    async def create_token(
        self,
        data: Dict[str, Any],
        session: AsyncSession,
        token_type: TokenType = TokenType.ACCESS,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a new token for a UUID-identified user.

        Args:
            data (Dict[str, Any]): Token payload (must contain 'sub' as UUID string).
            session (AsyncSession): Database session.
            token_type (TokenType): Type of token to create.
            expires_delta (Optional[timedelta]): Custom expiration time.

        Returns:
            str: Encoded JWT string.
        """
        return await self._create_token_impl(data, session, token_type, expires_delta)

    async def create_access_token(
        self,
        data: Dict[str, Any],
        session: AsyncSession,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Helper method to create an ACCESS token specifically.
        """
        return await self.create_token(data, session, TokenType.ACCESS, expires_delta)

    async def create_refresh_token(
        self,
        data: Dict[str, Any],
        session: AsyncSession,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Helper method to create a REFRESH token specifically.
        """
        return await self.create_token(data, session, TokenType.REFRESH, expires_delta)

    async def create_token_pair(
        self, data: Dict[str, Any], session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create both Access and Refresh tokens for a user session.

        Returns:
            Dict[str, Any]: A dictionary containing both tokens and expiry info.
        """
        return await self._create_token_pair_impl(data, session)

    async def validate_token(
        self, token: str, session: AsyncSession, token_type: Optional[TokenType] = None
    ) -> Dict[str, Any]:
        """
        Validate a token string against the database.

        Checks signature, expiry, and revocation status.
        """
        return await self._validate_token_impl(token, session, token_type=token_type)

    async def refresh_access_token(
        self, refresh_token: str, session: AsyncSession
    ) -> str:
        """
        Issue a new access token using a valid refresh token.
        """
        return await self._refresh_access_token_impl(refresh_token, session)

    async def revoke_token(self, token: str, session: AsyncSession) -> None:
        """
        Revoke a single token by its JTI.
        """
        await self._revoke_token_impl(token, session)

    async def revoke_all_tokens_for_user(
        self, user_id: Union[str, int], session: AsyncSession
    ) -> None:
        """
        Revoke all tokens belonging to a specific user UUID.
        """
        await self._revoke_all_for_user_impl(user_id, session)
