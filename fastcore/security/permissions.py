"""
Permission and role management for FastAPI applications.

This module provides utilities for implementing role-based access control (RBAC)
in FastAPI applications.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Union

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_db
from fastcore.errors.exceptions import NotFoundError, ValidationError
from fastcore.models.security import Permission as DBPermission
from fastcore.models.security import Role as DBRole
from fastcore.security.dependencies import get_current_user_data
from fastcore.security.repositories import PermissionRepository, RoleRepository


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


class RoleManager:
    """
    A utility class for managing roles and permissions directly in the database.

    This class provides methods for defining roles and permissions, and
    checking if users have specific permissions, all stored in the database.
    """

    async def add_role(
        self,
        session: AsyncSession,
        name: str,
        permissions: List[Union[str, Permission]] = None,
    ) -> DBRole:
        """
        Add a new role to the database.

        Args:
            session: Database session
            name: The name of the role
            permissions: Optional list of permissions for this role

        Returns:
            The created database role

        Raises:
            ValidationError: If a role with this name already exists
        """
        # Create repositories
        role_repo = RoleRepository(DBRole, session)
        perm_repo = PermissionRepository(DBPermission, session)

        # Check if role already exists
        try:
            existing = await role_repo.get_by_name(name)
            raise ValidationError(f"Role '{name}' already exists")
        except NotFoundError:
            # Role doesn't exist, we can create it
            pass

        # Create role
        db_role = await role_repo.create_if_not_exists(name)

        # Add permissions if provided
        if permissions:
            for perm in permissions:
                perm_name = perm.name if isinstance(perm, Permission) else perm

                if ":" in perm_name:
                    resource, action = perm_name.split(":")
                    db_perm = await perm_repo.create_if_not_exists(resource, action)
                    await role_repo.add_permission(db_role, db_perm)

        return db_role

    async def get_role(self, session: AsyncSession, name: str) -> Optional[DBRole]:
        """
        Get a role by name from the database.

        Args:
            session: Database session
            name: Role name

        Returns:
            The database role or None if not found
        """
        role_repo = RoleRepository(DBRole, session)
        try:
            return await role_repo.get_by_name(name)
        except NotFoundError:
            return None

    async def add_permission_to_role(
        self, session: AsyncSession, role_name: str, permission: Union[Permission, str]
    ) -> None:
        """
        Add a permission to a role in the database.

        Args:
            session: Database session
            role_name: The name of the role
            permission: The permission to add

        Raises:
            NotFoundError: If the role doesn't exist
        """
        role_repo = RoleRepository(DBRole, session)
        perm_repo = PermissionRepository(DBPermission, session)

        # Get role
        role = await role_repo.get_by_name(role_name)

        # Add permission
        perm_name = (
            permission.name if isinstance(permission, Permission) else permission
        )
        if ":" in perm_name:
            resource, action = perm_name.split(":")
            db_perm = await perm_repo.create_if_not_exists(resource, action)
            await role_repo.add_permission(role, db_perm)

    async def check_permission(
        self,
        session: AsyncSession,
        user_roles: List[str],
        permission: Union[Permission, str],
    ) -> bool:
        """
        Check if a user with the given roles has a specific permission.

        Args:
            session: Database session
            user_roles: The roles assigned to the user
            permission: The permission to check for

        Returns:
            True if the user has the permission, False otherwise
        """
        # Special case: superuser role always has all permissions
        if "superuser" in user_roles:
            return True

        role_repo = RoleRepository(DBRole, session)
        perm_name = (
            permission.name if isinstance(permission, Permission) else permission
        )

        # Check each role
        for role_name in user_roles:
            try:
                role = await role_repo.get_by_name(role_name)
                permissions = await role_repo.get_permissions(role)

                # Check for exact permission
                for db_perm in permissions:
                    if db_perm.name == perm_name:
                        return True

                    # Check for wildcard permissions
                    if ":" in perm_name:
                        resource, _ = perm_name.split(":")
                        if db_perm.name == f"{resource}:*":
                            return True

                    # Check for global wildcard
                    if db_perm.name == "*:*":
                        return True
            except NotFoundError:
                # Role doesn't exist, skip
                continue

        return False

    async def get_user_permissions(
        self, session: AsyncSession, user_roles: List[str]
    ) -> List[str]:
        """
        Get all permissions for a user with the given roles.

        Args:
            session: Database session
            user_roles: The roles assigned to the user

        Returns:
            A list of all permission strings for the user's roles
        """
        role_repo = RoleRepository(DBRole, session)
        permissions = set()

        for role_name in user_roles:
            try:
                role = await role_repo.get_by_name(role_name)
                db_perms = await role_repo.get_permissions(role)
                for perm in db_perms:
                    permissions.add(perm.name)
            except NotFoundError:
                # Role doesn't exist, skip
                continue

        return list(permissions)


# Create a global role manager instance
role_manager = RoleManager()


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
