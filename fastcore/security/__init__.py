"""
Security utilities for FastAPI applications.

This module provides authentication and authorization utilities
for FastAPI applications, including JWT authentication, OAuth support,
API keys, and role-based access control.
"""

from fastcore.security.apikey import APIKey, APIKeyAuth, get_api_key
from fastcore.security.auth import (
    JWTAuth,
    JWTAuthConfig,
    JWTPayload,
    create_access_token,
    decode_jwt_token,
    get_password_hash,
    verify_password,
)
from fastcore.security.dependencies import (
    get_current_active_user,
    get_current_superuser,
    get_current_user,
    require_permissions,
)
from fastcore.security.permissions import Permission, Role, RolePermission

__all__ = [
    # JWT Authentication
    "JWTAuth",
    "JWTAuthConfig",
    "JWTPayload",
    "create_access_token",
    "decode_jwt_token",
    "get_password_hash",
    "verify_password",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "require_permissions",
    # Role-based access control
    "Permission",
    "Role",
    "RolePermission",
    # API Key authentication
    "APIKey",
    "APIKeyAuth",
    "get_api_key",
]
