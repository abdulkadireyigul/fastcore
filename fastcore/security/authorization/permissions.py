"""
Permission and role management for FastAPI applications.

This module provides utilities for implementing role-based access control (RBAC)
in FastAPI applications.
"""

from typing import List, Union

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_db
from fastcore.security.authentication.dependencies import get_current_user_data

from .roles import role_manager


class Permission:
    """
    A class for defining and checking permissions.

    This class provides a way to define permissions in a structured way
    and check if a user has specific permissions.

    Example:
        ```python
        # Define permissions
        READ_USERS = Permission("users", "read")
        WRITE_USERS = Permission("users", "write")
        DELETE_USERS = Permission("users", "delete")

        # Check if user has permission
        user_permissions = ["users:read", "users:write"]
        if READ_USERS.check(user_permissions):
            # User can read users
            ...
        ```
    """

    def __init__(self, resource: str, action: str):
        """
        Initialize a new permission.

        Args:
            resource: The resource this permission applies to (e.g., "users", "products")
            action: The action this permission allows (e.g., "read", "write", "delete")
        """
        self.resource = resource
        self.action = action
        self.name = f"{resource}:{action}"

    def check(self, user_permissions: List[str]) -> bool:
        """
        Check if a user has this permission.

        Args:
            user_permissions: A list of permission strings the user has

        Returns:
            True if the user has this permission, False otherwise
        """
        # Check for exact permission
        if self.name in user_permissions:
            return True

        # Check for wildcard permissions
        if f"{self.resource}:*" in user_permissions:
            return True

        if "*:*" in user_permissions:
            return True

        return False

    def __str__(self) -> str:
        """Get the string representation of this permission."""
        return self.name

    def __repr__(self) -> str:
        """Get the debug representation of this permission."""
        return f"Permission({self.resource!r}, {self.action!r})"

    def __eq__(self, other) -> bool:
        """Check if two permissions are equal."""
        if isinstance(other, Permission):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        return False


# FastAPI dependencies for permission-based authorization
def has_permission(permission: Union[Permission, str]):
    """
    Create a dependency that checks if the current user has a specific permission.

    Args:
        permission: The permission to check for

    Returns:
        A dependency function that checks for the permission
    """

    async def check_permission(
        user_data: dict = Depends(get_current_user_data),
        session: AsyncSession = Depends(get_db),
    ):
        # Extract roles from the token
        roles = user_data.get("roles", [])

        # Check if the user has the required permission
        if not await role_manager.check_permission(session, roles, permission):
            from fastcore.errors.exceptions import ForbiddenError

            raise ForbiddenError(
                message=f"Permission denied. Required permission: {permission}"
            )

        return True

    return check_permission


def has_role(role: str):
    """
    Create a dependency that checks if the current user has a specific role.

    Args:
        role: The role to check for

    Returns:
        A dependency function that checks for the role
    """

    async def check_role(
        user_data: dict = Depends(get_current_user_data),
        session: AsyncSession = Depends(get_db),
    ):
        # Extract roles from the token
        roles = user_data.get("roles", [])

        # Check if the user has the required role
        if role not in roles:
            from fastcore.errors.exceptions import ForbiddenError

            raise ForbiddenError(message=f"Role '{role}' required for this operation")

        return True

    return check_role
