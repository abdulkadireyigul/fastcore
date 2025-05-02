"""
Token-related response schemas for authentication endpoints.
"""
from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """
    Standard response model for authentication tokens.

    This schema represents the response from a successful authentication
    request, containing access token information.

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
