import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.config import get_settings
from fastcore.errors.exceptions import DBError
from fastcore.logging.manager import ensure_logger
from fastcore.schemas.response.token import TokenResponse
from fastcore.security.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.tokens.models import Token, TokenType
from fastcore.security.tokens.repository import TokenRepository

from .utils import decode_token, validate_jwt_stateless

logger = ensure_logger(None, __name__)


async def create_token(
    data: Dict[str, Any],
    session: AsyncSession,
    token_type: TokenType = TokenType.ACCESS,
    expires_delta: Optional[timedelta] = None,
) -> str:
    settings = get_settings()
    token_id = str(uuid.uuid4())
    to_encode = data.copy()
    to_encode.update(
        {
            "jti": token_id,
            "type": token_type,
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
    )
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
    now = datetime.now(timezone.utc)
    to_encode.update({"exp": expire, "iat": now})
    from .utils import encode_jwt

    encoded_jwt = encode_jwt(to_encode)
    try:
        repo = TokenRepository(Token, session=session)
        await repo.create(
            {
                "token_id": token_id,
                "user_id": int(data.get("sub", -1)),
                "token_type": token_type,
                "expires_at": expire,
            }
        )
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating {token_type} token: {e}")
        raise DBError(message=str(e))
    logger.info(
        f"Created {token_type} token {token_id} for user {data.get('sub', 'unknown')}"
    )
    return encoded_jwt


async def create_access_token(
    data: Dict[str, Any],
    session: AsyncSession,
    expires_delta: Optional[timedelta] = None,
) -> str:
    return await create_token(data, session, TokenType.ACCESS, expires_delta)


async def create_refresh_token(
    data: Dict[str, Any],
    session: AsyncSession,
    expires_delta: Optional[timedelta] = None,
) -> str:
    return await create_token(data, session, TokenType.REFRESH, expires_delta)


async def create_token_pair(
    data: Dict[str, Any],
    session: AsyncSession,
) -> Dict[str, str]:
    access_token = await create_access_token(data, session)
    refresh_token = await create_refresh_token(data, session)
    # settings = get_settings()
    # expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    # return TokenResponse(
    #     access_token=access_token,
    #     refresh_token=refresh_token,
    #     token_type="bearer",
    #     # expires_in=expires_in,
    # ).dict()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def validate_token(
    token: str, session: AsyncSession, token_type: Optional[TokenType] = None
) -> Dict[str, Any]:
    payload = await validate_jwt_stateless(token, token_type)
    try:
        token_id = payload["jti"]
        repo = TokenRepository(Token, session=session)
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
    except (InvalidTokenError, ExpiredTokenError, RevokedTokenError):
        raise
    except Exception as e:
        logger.error(f"Error in stateful token validation: {e}")
        raise InvalidTokenError(
            message="Token validation failed", details={"error": str(e)}
        )


async def refresh_access_token(refresh_token: str, session: AsyncSession) -> str:
    try:
        payload = await validate_token(refresh_token, session, TokenType.REFRESH)
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError(message="Invalid token content")
        access_token = await create_access_token({"sub": user_id}, session)
        logger.info(f"Created new access token for user {user_id} via refresh")
        return access_token
    except (InvalidTokenError, ExpiredTokenError, RevokedTokenError):
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error refreshing access token: {e}")
        raise DBError(
            message=f"Error refreshing access token", details={"error": str(e)}
        )


async def revoke_token(token: str, session: AsyncSession) -> None:
    try:
        payload = await decode_token(token)
        token_id = payload.get("jti")
        user_id = payload.get("sub")
        if not token_id:
            raise InvalidTokenError(
                message="Token missing required 'jti' claim",
                details={"error": "Missing jti claim"},
            )
        if not user_id:
            raise InvalidTokenError(
                message="Token missing required 'sub' claim",
                details={"error": "Missing sub claim"},
            )
        repo = TokenRepository(Token, session=session)
        token_record = await repo.get_by_token_id(token_id)
        if not token_record:
            raise InvalidTokenError(
                message="Token not found in database", details={"token_id": token_id}
            )
        if token_record.revoked:
            logger.info(f"Token {token_id} already revoked")
            return
        await repo.revoke_token_for_user(int(user_id), token_id)
        await session.commit()
        logger.info(f"Successfully revoked token {token_id}")
    except InvalidTokenError:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error revoking token: {e}")
        raise DBError(message=f"Error revoking token", details={"error": str(e)})


async def revoke_all_tokens_for_user(user_id: int, session: AsyncSession) -> None:
    """
    Revoke all tokens for a given user.
    """
    try:
        repo = TokenRepository(Token, session=session)
        await repo.revoke_all_for_user(user_id)
        await session.commit()
        logger.info(f"Revoked all tokens for user {user_id}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error revoking all tokens for user {user_id}: {e}")
        raise DBError(message=f"Error revoking all tokens", details={"error": str(e)})
