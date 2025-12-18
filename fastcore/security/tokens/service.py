"""
Legacy Token Service Module.

This module provides the functional API for token operations, maintaining
backward compatibility with the original design of the library.

While it preserves the old function signatures (e.g., `create_access_token`),
it delegates all logic to the modern `BaseTokenService` implementation,
ensuring consistent behavior, logging, and error handling across the system.
"""

from datetime import timedelta
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.security.tokens.base_service import BaseTokenService
from fastcore.security.tokens.models import Token, TokenType
from fastcore.security.tokens.repository import TokenRepository

# --- Re-exports for Backward Compatibility ---
# These utilities are re-exported here so that legacy code importing them
# from `fastcore.security.tokens.service` continues to work without modification.
from .utils import decode_token, encode_jwt, validate_jwt_stateless


# --- Internal Implementation ---
class _LegacyTokenService(BaseTokenService[Token]):
    """
    Internal concrete implementation of the TokenService for legacy Integer IDs.
    It wires the `Token` model and `TokenRepository` to the generic base logic.
    """

    def __init__(self):
        super().__init__(model_cls=Token, repo_cls=TokenRepository)

    def _cast_user_id(self, user_id: Any) -> Any:
        """
        Override to enforce Integer IDs for legacy systems.

        The JWT 'sub' claim is always a string. This method converts it back
        to an integer to match the DB schema.
        """
        try:
            return int(user_id)
        except (ValueError, TypeError):
            # If it can't be cast (e.g., already None or bad data),
            # return as is and let the DB driver raise the error naturally.
            return user_id


# Singleton instance to handle functional API calls
_service_impl = _LegacyTokenService()


# --- Public Functional API ---


async def create_token(
    data: Dict[str, Any],
    session: AsyncSession,
    token_type: TokenType = TokenType.ACCESS,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new token for an integer-based user ID.

    Args:
        data (Dict[str, Any]): Token payload (must include 'sub').
        session (AsyncSession): Database session.
        token_type (TokenType): Type of token to create (default: ACCESS).
        expires_delta (Optional[timedelta]): Custom expiration time.

    Returns:
        str: The encoded JWT string.
    """
    return await _service_impl._create_token_impl(
        data, session, token_type, expires_delta
    )


async def create_access_token(
    data: Dict[str, Any],
    session: AsyncSession,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Helper function to create an ACCESS token.
    """
    return await create_token(data, session, TokenType.ACCESS, expires_delta)


async def create_refresh_token(
    data: Dict[str, Any],
    session: AsyncSession,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Helper function to create a REFRESH token.
    """
    return await create_token(data, session, TokenType.REFRESH, expires_delta)


async def create_token_pair(
    data: Dict[str, Any],
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    Create both Access and Refresh tokens for a user.

    Returns:
        Dict[str, Any]: Dictionary containing tokens and expiry info.
    """
    return await _service_impl._create_token_pair_impl(data, session)


async def validate_token(
    token: str, session: AsyncSession, token_type: Optional[TokenType] = None
) -> Dict[str, Any]:
    """
    Validate a token string against the database (Stateful Check).

    Args:
        token (str): The JWT string.
        session (AsyncSession): Database session.
        token_type (Optional[TokenType]): Expected token type.

    Returns:
        Dict[str, Any]: The decoded token payload.

    Raises:
        InvalidTokenError: If validation fails.
    """
    return await _service_impl._validate_token_impl(
        token, session, token_type=token_type
    )


async def refresh_access_token(refresh_token: str, session: AsyncSession) -> str:
    """
    Issue a new access token using a valid refresh token.
    """
    return await _service_impl._refresh_access_token_impl(refresh_token, session)


async def revoke_token(token: str, session: AsyncSession) -> None:
    """
    Revoke a single token by its JTI.
    """
    await _service_impl._revoke_token_impl(token, session)


async def revoke_all_tokens_for_user(user_id: int, session: AsyncSession) -> None:
    """
    Revoke all tokens belonging to a specific user ID (Integer).
    """
    await _service_impl._revoke_all_for_user_impl(user_id, session)
