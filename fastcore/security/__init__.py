"""
Security module initialization.

This module provides security features for FastAPI applications.
"""

from .authentication.dependencies import (
    get_current_user_data,
    get_optional_user_data,
    get_user_with_claim,
)

# Authentication
from .authentication.jwt import create_access_token, create_token_response, decode_token

# Authorization
from .authorization.permissions import Permission, has_permission, has_role
from .authorization.repositories import PermissionRepository, RoleRepository
from .authorization.roles import role_manager

# Crypto
from .crypto.password import hash_password, verify_password

# Manager
from .manager import setup_security

__all__ = [
    # Authentication
    "create_access_token",
    "decode_token",
    "create_token_response",
    "get_current_user_data",
    "get_optional_user_data",
    "get_user_with_claim",
    # Authorization
    "Permission",
    "role_manager",
    "has_permission",
    "has_role",
    "PermissionRepository",
    "RoleRepository",
    # Crypto
    "hash_password",
    "verify_password",
    # Setup
    "setup_security",
]
