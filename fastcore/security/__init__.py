"""
Security module root.

This module provides stateful authentication utilities 
for FastAPI applications, including JWT authentication, 
password handling, user authentication, and token management. 
All main security functions, models, helpers, and exceptions 
are exported from this module for easy access.

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

from fastcore.security.dependencies import (
    get_current_user_dependency,
    get_refresh_token_data,
    get_token_data,
    refresh_token,
)

# from fastcore.security.exceptions import (
#     ExpiredTokenError,
#     InvalidCredentialsError,
#     InvalidTokenError,
#     RevokedTokenError,
# )
from fastcore.security.manager import get_security_status, setup_security
from fastcore.security.password import get_password_hash, verify_password
from fastcore.security.tokens.models import TokenType
from fastcore.security.tokens.repository import TokenRepository
from fastcore.security.tokens.service import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    refresh_access_token,
    revoke_token,
    validate_token,
)
from fastcore.security.tokens.utils import encode_jwt, validate_jwt_stateless
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
    # "InvalidTokenError",
    # "ExpiredTokenError",
    # "RevokedTokenError",
    # "InvalidCredentialsError",
    # "AuthenticationError",
    # Token repository
    "TokenRepository",
    # Token utils
    "encode_jwt",
    "validate_jwt_stateless",
]
