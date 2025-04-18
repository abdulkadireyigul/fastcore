"""
FastAPI security dependencies for JWT authentication.

This module provides injectable dependencies for FastAPI routes
that require authentication.
"""

from typing import Any, Dict, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from fastcore.errors.exceptions import UnauthorizedError

from .jwt import decode_token

# Configure the OAuth2 password bearer scheme for token extraction from headers
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",  # This URL can be overridden in your app
    auto_error=False,  # Don't raise exceptions automatically
)


async def get_current_user_data(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    Extract and validate user data from a JWT token.

    This dependency extracts the Bearer token from the Authorization header and
    decodes it to get the user data in the token payload.

    Args:
        token: JWT token extracted from the Authorization header

    Returns:
        Dictionary containing the token payload data

    Raises:
        UnauthorizedError: If no token is provided or the token is invalid
    """
    if token is None:
        raise UnauthorizedError(message="Not authenticated")

    # Decode and validate the token
    payload = decode_token(token)

    # Ensure the token has a subject ("sub")
    if "sub" not in payload:
        raise UnauthorizedError(message="Invalid token payload")

    return payload


async def get_optional_user_data(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[Dict[str, Any]]:
    """
    Extract and validate user data from a JWT token if present.

    Similar to get_current_user_data, but doesn't raise an exception if no token
    is provided. Useful for routes that work differently for authenticated and
    unauthenticated users.

    Args:
        token: JWT token extracted from the Authorization header

    Returns:
        Dictionary containing the token payload data, or None if no valid token
    """
    if token is None:
        return None

    try:
        # Decode and validate the token
        payload = decode_token(token)

        # Ensure the token has a subject ("sub")
        if "sub" not in payload:
            return None

        return payload
    except UnauthorizedError:
        return None


# Advanced auth checks
def get_user_with_claim(claim_name: str, claim_value: Any = None):
    """
    Create a dependency that validates the user has a specific claim in their token.

    Args:
        claim_name: The name of the claim to check for
        claim_value: Optional specific value the claim should have

    Returns:
        A dependency function that checks for the claim

    Example:
        ```python
        @app.get("/org/{org_id}")
        async def get_org(
            org_id: str,
            user_data: dict = Depends(get_user_with_claim("org_id"))
        ):
            # User has org_id claim
            return {"org_id": org_id}

        @app.get("/admin-panel")
        async def admin_panel(
            user_data: dict = Depends(get_user_with_claim("is_admin", True))
        ):
            # User has is_admin claim with value True
            return {"message": "Admin panel"}
        ```
    """

    async def check_claim(user_data: dict = Depends(get_current_user_data)):
        if claim_name not in user_data:
            raise UnauthorizedError(
                message=f"Required claim '{claim_name}' not found in token"
            )

        if claim_value is not None and user_data[claim_name] != claim_value:
            raise UnauthorizedError(message=f"Claim '{claim_name}' has incorrect value")

        return user_data

    return check_claim
