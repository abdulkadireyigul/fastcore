"""
Role management for FastAPI applications.

This module provides utilities for managing roles and permissions in the database.
"""

from typing import List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.errors.exceptions import NotFoundError, ValidationError
from fastcore.models.security import Permission as DBPermission
from fastcore.models.security import Role as DBRole

from .permissions import Permission
from .repositories import PermissionRepository, RoleRepository


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
