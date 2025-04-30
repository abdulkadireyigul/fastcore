from typing import Any, Dict, Optional

import jwt  # type: ignore

from fastcore.config import get_settings
from fastcore.logging.manager import ensure_logger
from fastcore.security.exceptions import ExpiredTokenError, InvalidTokenError
from fastcore.security.tokens.models import TokenType

logger = ensure_logger(None, __name__)


def encode_jwt(payload: Dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token without validation.
    This function only decodes the token to access its payload,
    without validating if the token is valid, revoked, or expired.
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


async def validate_jwt_stateless(
    token: str, token_type: Optional[TokenType] = None, verify_exp: bool = True
) -> Dict[str, Any]:
    """
    Validate JWT token stateless properties (signature, claims, expiration).
    """
    settings = get_settings()
    try:
        audience = settings.JWT_ALLOWED_AUDIENCES or settings.JWT_AUDIENCE
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_aud": bool(audience),
                "verify_iss": bool(settings.JWT_ISSUER),
                "verify_exp": verify_exp,
            },
            audience=audience,
            issuer=settings.JWT_ISSUER,
        )
        if token_type and payload.get("type") != token_type:
            details = {
                "expected_type": token_type,
                "actual_type": payload.get("type", "unknown"),
            }
            raise InvalidTokenError(
                message=f"Invalid token type. Expected: {token_type}", details=details
            )
        if not payload.get("jti"):
            raise InvalidTokenError(
                message="Token missing required 'jti' claim",
                details={"error": "Missing jti claim"},
            )
        if not payload.get("sub"):
            raise InvalidTokenError(
                message="Token missing required 'sub' claim",
                details={"error": "Missing sub claim"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token used")
        raise ExpiredTokenError()
    # except jwt.InvalidAudienceError as e:
    #     logger.warning(f"Token with invalid audience: {e}")
    #     raise InvalidTokenError(
    #         message="Token has invalid audience",
    #         details={
    #             "error": str(e),
    #             "expected_audience": settings.JWT_ALLOWED_AUDIENCES
    #             or settings.JWT_AUDIENCE,
    #         },
    #     )
    # except jwt.InvalidIssuerError as e:
    #     logger.warning(f"Token with invalid issuer: {e}")
    #     raise InvalidTokenError(
    #         message="Token has invalid issuer",
    #         details={
    #             "error": str(e),
    #             "expected_issuer": settings.JWT_ISSUER,
    #         },
    #     )
    except jwt.PyJWTError as e:
        logger.error(f"Token validation error: {e}")
        raise InvalidTokenError(
            message="Invalid token signature or format", details={"error": str(e)}
        )
