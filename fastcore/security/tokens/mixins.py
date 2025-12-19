"""
Token Repository Mixins Module.

This module encapsulates reusable database logic for Token operations.
It is designed to be mixed into specific Repository classes (e.g., Legacy or UUID)
to provide standard CRUD capabilities without code duplication.
"""

from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar, Union

from sqlalchemy import select
from sqlalchemy import update as sqlalchemy_update

from fastcore.errors.exceptions import DBError
from fastcore.logging.manager import ensure_logger
from fastcore.security.tokens.types import TokenType

# Configure logger for this module
logger = ensure_logger(None, __name__)

# T represents the Token Model Type (e.g., Token or UUIDToken)
T = TypeVar("T")


class TokenRepositoryMixin(Generic[T]):
    """
    Mixin class providing standard CRUD operations for Token entities.

    This class is intended to be used with SQLAlchemy repositories.
    It expects the consuming class to provide:
    - self.model: The SQLAlchemy model class.
    - self.session: The active AsyncSession.
    """

    async def get_by_token_id(self, token_id: str) -> Optional[T]:
        """
        Retrieve a specific token record by its unique JTI (JWT ID).

        Args:
            token_id (str): The unique identifier of the token.

        Returns:
            Optional[T]: The token instance if found, otherwise None.

        Raises:
            DBError: If a database operation fails.
        """
        try:
            stmt = select(self.model).where(self.model.token_id == token_id)
            result = await self.session.execute(stmt)
            token = result.scalars().first()
            return token
        except Exception as e:
            logger.error(f"Error in get_by_token_id: {e}")
            raise DBError(message=str(e))

    async def get_by_user_id(self, user_id: Union[str, int]) -> List[T]:
        """
        Retrieve all token records associated with a specific user.

        Args:
            user_id (Union[str, int]): The user's ID (Integer for Legacy, UUID string for Modern).

        Returns:
            List[T]: A list of token instances belonging to the user.

        Raises:
            DBError: If a database operation fails.
        """
        try:
            stmt = select(self.model).where(self.model.user_id == user_id)
            result = await self.session.execute(stmt)
            tokens = result.scalars().all()
            return list(tokens)
        except Exception as e:
            logger.error(f"Error in get_by_user_id: {e}")
            raise DBError(message=str(e))

    async def get_refresh_token_for_user(self, user_id: Union[str, int]) -> Optional[T]:
        """
        Retrieve the most recent, active refresh token for a user.

        This method filters tokens based on:
        1. User ownership.
        2. Token type (must be REFRESH).
        3. Revocation status (must NOT be revoked).
        4. Expiry (must NOT be expired).

        Args:
            user_id (Union[str, int]): The user's ID.

        Returns:
            Optional[T]: The valid refresh token if found, otherwise None.

        Raises:
            DBError: If a database operation fails.
        """
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                select(self.model)
                .where(
                    self.model.user_id == user_id,
                    self.model.token_type == TokenType.REFRESH,
                    self.model.revoked
                    == False,  # noqa: E712 - Explicit check for False
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

    async def revoke_token_for_user(
        self, user_id: Union[str, int], token_id: str
    ) -> None:
        """
        Revoke a specific token for a user.

        This fetches the token first to ensure it belongs to the user and
        isn't already revoked before performing the update.

        Args:
            user_id (Union[str, int]): The owner of the token.
            token_id (str): The unique JTI of the token to revoke.

        Raises:
            DBError: If a database operation fails.
        """
        try:
            stmt = select(self.model).where(
                self.model.user_id == user_id,
                self.model.token_id == token_id,
                self.model.revoked == False,  # noqa: E712
            )
            result = await self.session.execute(stmt)
            token = result.scalars().first()

            if token:
                token.revoked = True
                await self.session.flush()
                logger.info(f"Revoked token {token_id} for user {user_id}")
            else:
                logger.warning(
                    f"Token {token_id} for user {user_id} not found or already revoked"
                )
        except Exception as e:
            logger.error(f"Error in revoke_token_for_user: {e}")
            raise DBError(message=str(e))

    async def revoke_all_for_user(
        self, user_id: Union[str, int], exclude_token_id: Optional[str] = None
    ) -> None:
        """
        Revoke all active tokens for a specific user.

        Optionally keeps one token active (e.g., the current session's token)
        while revoking all others (Refresh Rotation strategy).

        Args:
            user_id (Union[str, int]): The user's ID.
            exclude_token_id (Optional[str]): A token ID (JTI) to skip revocation.

        Raises:
            DBError: If a database operation fails.
        """
        try:
            # Build conditions list
            conditions = [
                self.model.user_id == user_id,
                self.model.revoked == False,  # noqa: E712
            ]

            # Add exclusion if provided
            if exclude_token_id:
                conditions.append(self.model.token_id != exclude_token_id)

            # Perform bulk update
            # Note: We use self.model.__table__ for bulk updates to avoid ORM overhead
            stmt = (
                sqlalchemy_update(self.model.__table__)
                .where(*conditions)
                .values(revoked=True)
            )
            result = await self.session.execute(stmt)
            await self.session.flush()

            # Rowcount attribute availability depends on the DB driver
            rows_affected = result.rowcount if hasattr(result, "rowcount") else -1
            logger.info(f"Revoked {rows_affected} tokens for user {user_id}")

        except Exception as e:
            logger.error(f"Error in revoke_all_for_user: {e}")
            raise DBError(message=str(e))
