"""
Security module initialization.

This module provides security features for FastAPI applications.
"""

from .auth import create_access_token, create_token_response, decode_token
from .dependencies import (
    get_current_user_data,
    get_optional_user_data,
    get_user_with_claim,
)
from .manager import setup_security
from .password import hash_password, verify_password
from .permissions import Permission, has_permission, has_role, role_manager

__all__ = [
    # Auth
    "create_access_token",
    "decode_token",
    "create_token_response",
    # Dependencies
    "get_current_user_data",
    "get_optional_user_data",
    "get_user_with_claim",
    # Password
    "hash_password",
    "verify_password",
    # Permissions
    "Permission",
    "role_manager",
    "has_permission",
    "has_role",
    # Setup
    "setup_security",
]
