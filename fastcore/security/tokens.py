"""
Token management utilities.

This module provides functions for creating, validating, and revoking JWT tokens,
implementing a stateful token system despite using JWTs.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.config import get_settings
from fastcore.db.repository import BaseRepository
from fastcore.errors.exceptions import DBError
from fastcore.logging.manager import ensure_logger
from fastcore.security.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.models import Token, TokenType

# Configure logger
logger = ensure_logger(None, __name__)


class TokenRepository(BaseRepository[Token]):
    """Repository for token operations."""

    async def get_by_token_id(self, token_id: str) -> Optional[Token]:
        """Get a token record by its token_id."""
        try:
            stmt = select(self.model).where(self.model.token_id == token_id)
            result = await self.session.execute(stmt)
            token = result.scalars().first()
            return token
        except Exception as e:
            logger.error(f"Error in get_by_token_id: {e}")
            raise DBError(message=str(e))

    async def revoke_token(self, token_id: str) -> None:
        """Mark a token as revoked."""
        token = await self.get_by_token_id(token_id)
        if token:
            token.revoked = True
            await self.session.flush()
            logger.info(f"Revoked token {token_id}")

    async def revoke_all_user_tokens(
        self, user_id: str, exclude_token_id: Optional[str] = None
    ) -> None:
        """
        Revoke all tokens for a specific user.

        Args:
            user_id: User ID to revoke tokens for
            exclude_token_id: Optional token ID to exclude from revocation
        """
        try:
            stmt = select(self.model).where(
                self.model.user_id == user_id,
                self.model.revoked == False,  # noqa: E712
            )
            if exclude_token_id:
                stmt = stmt.where(self.model.token_id != exclude_token_id)

            result = await self.session.execute(stmt)
            tokens = result.scalars().all()

            for token in tokens:
                token.revoked = True

            await self.session.flush()
            logger.info(f"Revoked {len(tokens)} tokens for user {user_id}")
        except Exception as e:
            logger.error(f"Error in revoke_all_user_tokens: {e}")
            raise DBError(message=str(e))

    async def get_refresh_token_for_user(self, user_id: str) -> Optional[Token]:
        """Get a valid refresh token for a user."""
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                select(self.model)
                .where(
                    self.model.user_id == user_id,
                    self.model.token_type == TokenType.REFRESH,
                    self.model.revoked == False,  # noqa: E712
                    self.model.expires_at > now,
                )
                .order_by(self.model.created_at.desc())
            )

            result = await self.session.execute(stmt)
            token = result.scalars().first()
            return token
        except Exception as e:
            logger.error(f"Error in get_refresh_token_for_user: {e}")
            raise DBError(message=str(e))


async def create_access_token(
    data: Dict[str, Any],
    session: AsyncSession,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new JWT access token.

    Args:
        data: The payload data to encode in the token
        session: Database session for storing token metadata
        expires_delta: Optional custom expiration time

    Returns:
        The encoded JWT token as a string
    """
    settings = get_settings()

    # Generate a unique ID for this token
    token_id = str(uuid.uuid4())

    # Add token_id to the payload
    to_encode = data.copy()
    to_encode.update(
        {
            "jti": token_id,
            "type": TokenType.ACCESS,
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
    )

    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add issued at time (iat) and expiration (exp)
    now = datetime.now(timezone.utc)
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
        }
    )

    # Create JWT token
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    try:
        # Store token metadata in database
        repo = TokenRepository(Token, session)
        await repo.create(
            {
                "token_id": token_id,
                "user_id": str(data.get("sub", "unknown")),
                "token_type": TokenType.ACCESS,
                "expires_at": expire,
            }
        )
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise DBError(message=str(e))

    logger.info(
        f"Created access token {token_id} for user {data.get('sub', 'unknown')}"
    )
    return encoded_jwt


async def create_refresh_token(
    data: Dict[str, Any],
    session: AsyncSession,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new JWT refresh token.

    Args:
        data: The payload data to encode in the token
        session: Database session for storing token metadata
        expires_delta: Optional custom expiration time

    Returns:
        The encoded JWT refresh token as a string
    """
    settings = get_settings()

    # Generate a unique ID for this token
    token_id = str(uuid.uuid4())

    # Add token_id to the payload
    to_encode = data.copy()
    to_encode.update(
        {
            "jti": token_id,
            "type": TokenType.REFRESH,
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
    )

    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

    # Add issued at time (iat) and expiration (exp)
    now = datetime.now(timezone.utc)
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
        }
    )

    # Create JWT token
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    try:
        # Store token metadata in database
        repo = TokenRepository(Token, session)
        await repo.create(
            {
                "token_id": token_id,
                "user_id": str(data.get("sub", "unknown")),
                "token_type": TokenType.REFRESH,
                "expires_at": expire,
            }
        )
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise DBError(message=str(e))

    logger.info(
        f"Created refresh token {token_id} for user {data.get('sub', 'unknown')}"
    )
    return encoded_jwt


async def create_token_pair(
    data: Dict[str, Any],
    session: AsyncSession,
) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user.

    Args:
        data: The payload data to encode in the tokens
        session: Database session for storing token metadata

    Returns:
        Dictionary containing access_token and refresh_token
    """
    access_token = await create_access_token(data, session)
    refresh_token = await create_refresh_token(data, session)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token without validation.

    This function only decodes the token to access its payload,
    without validating if the token is valid, revoked, or expired.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded token payload

    Raises:
        InvalidTokenError: If the token is malformed or invalid
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": True, "verify_exp": False},
        )
        return payload
    except jwt.PyJWTError as e:
        logger.error(f"Token decode error: {e}")
        raise InvalidTokenError(details={"error": str(e)})


async def validate_token(
    token: str, session: AsyncSession, token_type: Optional[TokenType] = None
) -> Dict[str, Any]:
    """
    Validate a JWT token including stateful checks.

    This function performs both stateless JWT validation and stateful checks
    against the database to ensure the token hasn't been revoked.

    Args:
        token: The JWT token to validate
        session: Database session for stateful validation
        token_type: Optional expected token type (access or refresh)

    Returns:
        The decoded token payload if valid

    Raises:
        InvalidTokenError: If the token is malformed or invalid
        ExpiredTokenError: If the token has expired
        RevokedTokenError: If the token has been revoked
    """
    settings = get_settings()

    try:
        # First do stateless validation with audience validation
        audience = settings.JWT_ALLOWED_AUDIENCES or settings.JWT_AUDIENCE
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_aud": bool(audience),  # Only verify if audience is set
                "verify_iss": bool(settings.JWT_ISSUER),  # Only verify if issuer is set
            },
            audience=audience,
            issuer=settings.JWT_ISSUER,
        )

        # Check token type if specified
        if token_type and payload.get("type") != token_type:
            details = {
                "expected_type": token_type,
                "actual_type": payload.get("type", "unknown"),
            }
            raise InvalidTokenError(
                message=f"Invalid token type. Expected: {token_type}", details=details
            )

        # Then do stateful validation
        token_id = payload.get("jti")
        if not token_id:
            raise InvalidTokenError(
                message="Token missing required 'jti' claim",
                details={"error": "Missing jti claim"},
            )

        # Check token in database
        repo = TokenRepository(Token, session)
        token_record = await repo.get_by_token_id(token_id)

        if not token_record:
            raise InvalidTokenError(
                message="Token not found in database", details={"token_id": token_id}
            )

        if token_record.revoked:
            raise RevokedTokenError(
                details={"token_id": token_id, "revoked_at": token_record.updated_at}
            )

        return payload

    except jwt.InvalidAudienceError as e:
        logger.warning(f"Token with invalid audience: {e}")
        raise InvalidTokenError(
            message="Token has invalid audience",
            details={
                "error": str(e),
                "expected_audience": settings.JWT_ALLOWED_AUDIENCES
                or settings.JWT_AUDIENCE,
            },
        )
    except jwt.InvalidIssuerError as e:
        logger.warning(f"Token with invalid issuer: {e}")
        raise InvalidTokenError(
            message="Token has invalid issuer",
            details={
                "error": str(e),
                "expected_issuer": settings.JWT_ISSUER,
            },
        )
    except jwt.ExpiredSignatureError:
        logger.warning(f"Expired token used")
        raise ExpiredTokenError()
    except jwt.PyJWTError as e:
        logger.error(f"Token validation error: {e}")
        raise InvalidTokenError(
            message="Invalid token signature or format", details={"error": str(e)}
        )


async def refresh_access_token(refresh_token: str, session: AsyncSession) -> str:
    """
    Create a new access token using a valid refresh token.

    Args:
        refresh_token: A valid refresh token
        session: Database session for token operations

    Returns:
        A new access token

    Raises:
        InvalidTokenError: If the refresh token is invalid
        ExpiredTokenError: If the refresh token has expired
        RevokedTokenError: If the refresh token has been revoked
    """
    # Validate the refresh token
    payload = await validate_token(refresh_token, session, TokenType.REFRESH)

    # Create a new access token with the same subject
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError(message="Invalid token content")

    # Create a new access token
    access_token = await create_access_token({"sub": user_id}, session)

    logger.info(f"Created new access token for user {user_id} via refresh")
    return access_token


async def revoke_token(token: str, session: AsyncSession) -> None:
    """
    Revoke a JWT token.

    Args:
        token: The JWT token to revoke
        session: Database session for token operations

    Raises:
        InvalidTokenError: If the token is malformed or invalid
        DBError: If there is a database error
    """
    try:
        # Decode the token to get the token_id
        payload = await decode_token(token)
        token_id = payload.get("jti")

        if not token_id:
            raise InvalidTokenError(
                message="Token missing required 'jti' claim",
                details={"error": "Missing jti claim"},
            )

        # Revoke the token in the database
        repo = TokenRepository(Token, session)
        token_record = await repo.get_by_token_id(token_id)

        if not token_record:
            raise InvalidTokenError(
                message="Token not found in database", details={"token_id": token_id}
            )

        if token_record.revoked:
            # Already revoked, just return
            logger.info(f"Token {token_id} already revoked")
            return

        await repo.revoke_token(token_id)
        logger.info(f"Successfully revoked token {token_id}")

    except InvalidTokenError:
        # Re-raise security exceptions
        raise
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        raise DBError(message=f"Error revoking token", details={"error": str(e)})
