from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from fastcore.db.repository import BaseRepository
from fastcore.errors.exceptions import DBError
from fastcore.logging.manager import ensure_logger

from .models import Token, TokenType

logger = ensure_logger(None, __name__)


class TokenRepository(BaseRepository[Token]):
    """Repository for token operations."""

    async def get_by_token_id(self, token_id: str) -> Optional[Token]:
        try:
            stmt = select(self.model).where(self.model.token_id == token_id)
            result = await self.session.execute(stmt)
            token = result.scalars().first()
            return token
        except Exception as e:
            logger.error(f"Error in get_by_token_id: {e}")
            raise DBError(message=str(e))

    async def get_by_user_id(self, user_id: int) -> list[Token]:
        try:
            stmt = select(self.model).where(self.model.user_id == user_id)
            result = await self.session.execute(stmt)
            tokens = result.scalars().all()
            return tokens
        except Exception as e:
            logger.error(f"Error in get_by_user_id: {e}")
            raise DBError(message=str(e))

    async def get_refresh_token_for_user(self, user_id: int) -> Optional[Token]:
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

    async def revoke_token_for_user(self, user_id: int, token_id: str) -> None:
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
        self, user_id: int, exclude_token_id: Optional[str] = None
    ) -> None:
        try:
            conditions = [
                self.model.user_id == user_id,
                self.model.revoked == False,  # noqa: E712
            ]
            if exclude_token_id:
                conditions.append(self.model.token_id != exclude_token_id)
            from sqlalchemy import update as sqlalchemy_update

            stmt = (
                sqlalchemy_update(self.model.__table__)
                .where(*conditions)
                .values(revoked=True)
            )
            result = await self.session.execute(stmt)
            await self.session.flush()
            rows_affected = result.rowcount if hasattr(result, "rowcount") else -1
            logger.info(f"Revoked {rows_affected} tokens for user {user_id}")
        except Exception as e:
            logger.error(f"Error in revoke_all_for_user: {e}")
            raise DBError(message=str(e))
