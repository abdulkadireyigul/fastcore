"""
Token-related response schemas for authentication endpoints.

Limitations:
- Envelope structure is fixed; customization requires subclassing or code changes
- Only basic token fields are included by default
- No built-in support for localization or advanced metadata
"""
from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """
    Standard response model for authentication tokens.

    Features:
    - Standardized schema for authentication token responses
    - Includes access and refresh tokens, expiration info

    Limitations:
    - Envelope structure is fixed; customization requires subclassing or code changes
    - Only basic token fields are included by default
    - No built-in support for localization or advanced metadata

    Attributes:
        token_type: The type of token, typically "bearer"
        access_token: The JWT access token
        refresh_token: Optional refresh token for token renewal
        access_expires_in: Expiration time in seconds for the access token
        refresh_expires_in: Expiration time in seconds for the refresh token
    """

    token_type: str = Field(
        default="bearer", description="Type of authentication token"
    )
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(
        default=None, description="Optional refresh token"
    )
    access_expires_in: Optional[int] = Field(
        default=None, description="Access token expiration time in seconds"
    )
    refresh_expires_in: Optional[int] = Field(
        default=None, description="Refresh token expiration time in seconds"
    )
