"""
Password hashing and verification utilities.

Uses bcrypt for secure password hashing.
"""

from passlib.context import CryptContext

# Configure password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Work factor - higher is more secure but slower
)


def hash_password(plain_password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        plain_password: Plain text password to hash

    Returns:
        Securely hashed password string
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches the hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
