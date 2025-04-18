"""
Authorization module for FastAPI applications.

This module provides functionality for role-based access control (RBAC)
and permission checking.
"""

from .permissions import Permission, has_permission, has_role
from .repositories import PermissionRepository, RoleRepository
from .roles import role_manager

__all__ = [
    "Permission",
    "has_permission",
    "has_role",
    "role_manager",
    "PermissionRepository",
    "RoleRepository",
]
