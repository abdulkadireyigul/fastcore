"""
JWT authentication utilities for token generation and validation.

This module provides functions for creating and validating JWT tokens
in a way that is not tied to any specific user model or schema.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import jwt

from fastcore.config.settings import settings
from fastcore.errors.exceptions import UnauthorizedError
from fastcore.schemas.response import TokenResponse


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT access token.

    Args:
        data: Data to encode in the token payload
        expires_delta: Optional expiration time, defaults to settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        JWT token string

    Note:
        The 'data' dict should contain at least a 'sub' (subject) claim to identify the token holder.
        Example: {"sub": "user-123", "role": "admin"}
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add standard claims if not present
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
    )

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Validate and decode a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload as a dictionary

    Raises:
        UnauthorizedError: If token validation fails
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(message="Token expired")
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(message=f"Invalid token: {str(e)}")


def create_token_response(data: Dict[str, Any]) -> TokenResponse:
    """
    Create a token response suitable for returning in API responses.

    Args:
        data: Data to encode in token payload

    Returns:
        TokenResponse object with token details
    """
    access_token = create_access_token(data)
    return TokenResponse(
        token_type="bearer",
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
    )
