"""
Base Token Service Module.

This module defines the abstract base logic for the token lifecycle management.
It implements the "Template Method" pattern, providing core logic for:
- Token Creation (Access & Refresh)
- Token Validation (Stateless & Stateful)
- Token Revocation
- Token Refreshing

It is designed to be agnostic of the underlying ID type (UUID vs Integer),
enforcing DRY (Don't Repeat Yourself) principles across the application.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generic, Optional, Type, TypeVar, Union

from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db.repository import BaseRepository
from fastcore.errors.exceptions import (
    DBError,
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.logging.manager import ensure_logger
from fastcore.schemas.response.token import TokenResponse
from fastcore.security.manager import get_security_settings
from fastcore.security.tokens.types import TokenType
from fastcore.security.tokens.utils import (
    decode_token,
    encode_jwt,
    validate_jwt_stateless,
)

# Configure logger
logger = ensure_logger(None, __name__)

# ModelT represents the SQLAlchemy Model (e.g., Token or UUIDToken)
ModelT = TypeVar("ModelT")


class BaseTokenService(Generic[ModelT]):
    """
    Abstract Base Class for Token Services.

    This class handles the orchestration of token operations. It delegates
    database interactions to the injected repository class while maintaining
    the core business logic for JWT handling.
    """

    def __init__(self, model_cls: Type[ModelT], repo_cls: Type[BaseRepository]):
        """
        Initialize the BaseTokenService.

        Args:
            model_cls (Type[ModelT]): The SQLAlchemy model class to be used.
            repo_cls (Type[BaseRepository]): The Repository class used for persistence.
        """
        self.model_cls = model_cls
        self.repo_cls = repo_cls

    def _cast_user_id(self, user_id: Any) -> Any:
        """
        Hook method to cast user_id to the correct type for the database.

        By default, it returns the value as-is (suitable for UUID/String IDs).
        Legacy implementations should override this to cast to Integer.
        """
        return user_id

    async def _create_token_impl(
        self,
        data: Dict[str, Any],
        session: AsyncSession,
        token_type: TokenType,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Internal implementation of token creation.

        Generates a JWT, calculates expiry, and persists the token metadata to the database.

        Args:
            data (Dict[str, Any]): The payload data (must include 'sub').
            session (AsyncSession): Database session.
            token_type (TokenType): ACCESS or REFRESH.
            expires_delta (Optional[timedelta]): Custom expiry duration.

        Returns:
            str: The encoded JWT string.

        Raises:
            ValueError: If 'sub' claim is missing.
            DBError: If persistence fails.
        """
        # 1. Input Validation
        raw_user_id = data.get("sub")
        if raw_user_id is None:
            raise ValueError("Subject (sub) claim is missing in token data")

        # 2. Configuration & Defaults
        settings = get_security_settings()
        token_id = str(uuid.uuid4())

        # 3. Expiry Calculation
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            if token_type == TokenType.ACCESS:
                expire = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                )
            else:
                expire = datetime.now(timezone.utc) + timedelta(
                    days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
                )

        # 4. Payload Construction
        to_encode = data.copy()
        to_encode.update(
            {
                "jti": token_id,
                "type": token_type,
                "aud": settings.JWT_AUDIENCE,
                "iss": settings.JWT_ISSUER,
                "exp": expire,
                "iat": datetime.now(timezone.utc),
            }
        )

        encoded_jwt = encode_jwt(to_encode)

        # 5. Persistence
        try:
            db_user_id = self._cast_user_id(raw_user_id)

            # Instantiate the repository dynamically
            repo = self.repo_cls(self.model_cls, session=session)
            await repo.create(
                {
                    "token_id": token_id,
                    "user_id": db_user_id,  # Int or Str is handled by the specific DB driver
                    "token_type": token_type,
                    "expires_at": expire,
                }
            )
            await session.commit()

            logger.info(f"Created {token_type} token {token_id} for user {db_user_id}")  # type: ignore

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating {token_type} token: {e}")  # type: ignore
            raise DBError(message=str(e))

        return encoded_jwt

    async def _create_token_pair_impl(
        self, data: Dict[str, Any], session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Creates both access and refresh tokens and formats the response.

        This method ensures that the returned expiry times match the actual
        claims within the generated JWTs.

        Args:
            data (Dict[str, Any]): User data payload.
            session (AsyncSession): Database session.

        Returns:
            Dict[str, Any]: A dictionary containing tokens and metadata (Pydantic model dump).
        """
        # Create Access Token
        access_token = await self._create_token_impl(data, session, TokenType.ACCESS)

        # Calculate Access Token Expiry (from decoded payload to be exact)
        access_payload = decode_token(access_token)
        access_expires_at = access_payload.get("exp")

        if access_expires_at:
            access_expires_at_dt = datetime.fromtimestamp(
                access_expires_at, tz=timezone.utc
            )
        else:
            # Fallback to settings if exp claim is missing (rare case)
            access_expires_at_dt = datetime.now(timezone.utc) + timedelta(
                minutes=get_security_settings().JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )

        access_expires_delta = access_expires_at_dt - datetime.now(timezone.utc)

        # Create Refresh Token
        refresh_token = await self._create_token_impl(data, session, TokenType.REFRESH)

        # Calculate Refresh Token Expiry
        refresh_payload = decode_token(refresh_token)
        refresh_expires_at = refresh_payload.get("exp")

        if refresh_expires_at:
            refresh_expires_at_dt = datetime.fromtimestamp(
                refresh_expires_at, tz=timezone.utc
            )
        else:
            # Fallback to settings
            refresh_expires_at_dt = datetime.now(timezone.utc) + timedelta(
                days=get_security_settings().JWT_REFRESH_TOKEN_EXPIRE_DAYS
            )

        refresh_expires_delta = refresh_expires_at_dt - datetime.now(timezone.utc)

        logger.info(f"Created token pair for user {data.get('sub', 'unknown')}")  # type: ignore

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_in=int(access_expires_delta.total_seconds()),
            refresh_expires_in=int(refresh_expires_delta.total_seconds()),
            token_type="bearer",
        ).model_dump()

    async def _validate_token_impl(
        self,
        token: str,
        session: AsyncSession,
        token_type: Optional[TokenType] = None,
    ) -> Dict[str, Any]:
        """
        Internal implementation of stateful token validation.

        Checks the JWT signature (stateless) AND verifies the token exists
        and is not revoked in the database (stateful).

        Args:
            token (str): The JWT string.
            session (AsyncSession): Database session.
            token_type (Optional[TokenType]): Expected token type (Access/Refresh).

        Returns:
            Dict[str, Any]: The decoded token payload.

        Raises:
            InvalidTokenError: If signature is invalid or token not found/revoked.
            ExpiredTokenError: If the token has expired.
            RevokedTokenError: If the token is explicitly marked as revoked.
        """
        try:
            # 1. Stateless Check (Signature & Expiry)
            payload = await validate_jwt_stateless(token, token_type)
            token_id = payload["jti"]

            # 2. Stateful Check (DB Existence & Revocation)
            repo = self.repo_cls(self.model_cls, session=session)
            token_record = await repo.get_by_token_id(token_id)  # type: ignore

            if not token_record:
                raise InvalidTokenError(
                    message="Token not found in database",
                    details={"token_id": token_id},
                )

            if token_record.revoked:
                raise RevokedTokenError(details={"token_id": token_id})

            return payload

        except (InvalidTokenError, ExpiredTokenError, RevokedTokenError):
            raise
        except Exception as e:
            logger.error(f"Error in stateful token validation: {e}")  # type: ignore
            raise InvalidTokenError(
                message="Token validation failed", details={"error": str(e)}
            )

    async def _refresh_access_token_impl(
        self, refresh_token: str, session: AsyncSession
    ) -> str:
        """
        Validates a refresh token and issues a new access token.

        Args:
            refresh_token (str): The valid refresh token.
            session (AsyncSession): Database session.

        Returns:
            str: A new access token string.

        Raises:
            InvalidTokenError: If the refresh token is invalid or missing sub claim.
            DBError: If database operations fail.
        """
        try:
            # Validate the Refresh Token
            payload = await self._validate_token_impl(
                refresh_token, session, TokenType.REFRESH
            )

            user_id = payload.get("sub")
            if not user_id:
                raise InvalidTokenError(message="Invalid token content: missing 'sub'")

            # Create new Access Token
            access_token = await self._create_token_impl(
                {"sub": user_id}, session, TokenType.ACCESS
            )

            logger.info(f"Created new access token for user {user_id} via refresh")  # type: ignore
            return access_token

        except (InvalidTokenError, ExpiredTokenError, RevokedTokenError):
            raise

        except Exception as e:
            await session.rollback()
            logger.error(f"Error refreshing access token: {e}")  # type: ignore
            raise DBError(
                message=f"Error refreshing access token", details={"error": str(e)}
            )

    async def _revoke_token_impl(self, token: str, session: AsyncSession) -> None:
        """
        Internal implementation of token revocation.

        Decodes the token to get the ID, then marks it as revoked in the database.
        """
        try:
            payload = decode_token(token)
            token_id = payload.get("jti")
            raw_user_id = payload.get("sub")

            if not token_id or not raw_user_id:
                raise InvalidTokenError(
                    message="Token missing required claims (jti or sub)"
                )

            db_user_id = self._cast_user_id(raw_user_id)

            repo = self.repo_cls(self.model_cls, session=session)
            token_record = await repo.get_by_token_id(token_id)  # type: ignore

            if not token_record:
                raise InvalidTokenError(
                    message="Token not found", details={"token_id": token_id}
                )

            if token_record.revoked:
                logger.info(f"Token {token_id} already revoked")  # type: ignore
                return

            await repo.revoke_token_for_user(db_user_id, token_id)  # type: ignore
            await session.commit()
            logger.info(f"Successfully revoked token {token_id}")  # type: ignore

        except InvalidTokenError:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Error revoking token: {e}")  # type: ignore
            raise DBError(message="Error revoking token", details={"error": str(e)})

    async def _revoke_all_for_user_impl(
        self, user_id: Union[str, int], session: AsyncSession
    ) -> None:
        """
        Internal implementation to revoke all tokens for a user.
        """
        try:
            db_user_id = self._cast_user_id(user_id)
            repo = self.repo_cls(self.model_cls, session=session)
            await repo.revoke_all_for_user(db_user_id)  # type: ignore
            await session.commit()
            logger.info(f"Revoked all tokens for user {db_user_id}")  # type: ignore
        except Exception as e:
            await session.rollback()
            logger.error(f"Error revoking all tokens for user {user_id}: {e}")  # type: ignore
            raise DBError(
                message="Error revoking all tokens", details={"error": str(e)}
            )
