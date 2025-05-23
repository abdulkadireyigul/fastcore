"""
Password handling utilities.

This module provides functions for hashing and verifying passwords
using bcrypt through the passlib library.

Limitations:
- Only password-based JWT authentication is included by default
- No OAuth2 authorization code, implicit, or client credentials flows
- No social login (Google, Facebook, etc.)
- No multi-factor authentication
- No user registration or management flows (only protocols/interfaces)
- No advanced RBAC or permission system
- No API key support
- Stateless JWT blacklisting/revocation requires stateful DB tracking
"""

from passlib.context import CryptContext  # type: ignore

# Create a password context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Generate a bcrypt hash for a plaintext password.

    Features:
    - Uses passlib's bcrypt hashing

    Limitations:
    - Only password-based JWT authentication is included by default
    - No advanced RBAC or permission system

    Args:
        password: The plaintext password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plaintext password matches a hashed password.

    Features:
    - Uses passlib's bcrypt verification

    Limitations:
    - Only password-based JWT authentication is included by default
    - No advanced RBAC or permission system

    Args:
        plain_password: The plaintext password to verify
        hashed_password: The hashed password to check against

    Returns:
        True if the password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False
