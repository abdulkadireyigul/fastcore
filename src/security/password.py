"""
Password handling utilities.

This module provides functions for hashing and verifying passwords
using bcrypt through the passlib library.
"""

from passlib.context import CryptContext

# Create a password context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Generate a bcrypt hash for a plaintext password.

    Args:
        password: The plaintext password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plaintext password matches a hashed password.

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
