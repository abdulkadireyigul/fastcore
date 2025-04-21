"""
Security utilities for FastAPI applications.

This module provides stateful authentication utilities
for FastAPI applications, including JWT authentication,
password handling, and token management.
"""

from fastcore.security.dependencies import (
    get_current_user_dependency,
    get_refresh_token_data,
    get_token_data,
    refresh_token,
)
from fastcore.security.exceptions import (
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.manager import get_security_status, setup_security
from fastcore.security.models import TokenType
from fastcore.security.password import get_password_hash, verify_password
from fastcore.security.tokens import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    refresh_access_token,
    revoke_all_tokens,
    revoke_token,
    validate_token,
)
from fastcore.security.users import (
    AuthenticationError,
    BaseUserAuthentication,
    UserAuthentication,
)

__all__ = [
    # Core token functions
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_token",
    "validate_token",
    "refresh_access_token",
    "revoke_token",
    "revoke_all_tokens",
    # Password utilities
    "get_password_hash",
    "verify_password",
    # Models and types
    "TokenType",
    # Setup function and status
    "setup_security",
    "get_security_status",
    # FastAPI dependencies
    "get_token_data",
    "get_current_user_dependency",
    "get_refresh_token_data",
    "refresh_token",
    # User authentication
    "UserAuthentication",
    "BaseUserAuthentication",
    # Exceptions
    "InvalidTokenError",
    "ExpiredTokenError",
    "RevokedTokenError",
    "InvalidCredentialsError",
    "AuthenticationError",
]
