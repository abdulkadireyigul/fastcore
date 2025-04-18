"""
Database repositories for security-related entities.

These repositories provide database operations for roles and permissions.
"""

from typing import List, Optional

from sqlalchemy import select

from fastcore.db.repository import BaseRepository
from fastcore.errors.exceptions import NotFoundError
from fastcore.models.security import Permission, Role


class PermissionRepository(BaseRepository[Permission]):
    """Repository for database permission operations."""

    async def get_by_name(self, name: str) -> Permission:
        """
        Get a permission by its name.

        Args:
            name: Permission name in format "resource:action"

        Returns:
            The permission object

        Raises:
            NotFoundError: If permission doesn't exist
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.execute(stmt)
        permission = result.scalar_one_or_none()

        if permission is None:
            raise NotFoundError(resource_type="Permission", resource_id=name)

        return permission

    async def find_by_name(self, name: str) -> Optional[Permission]:
        """
        Find a permission by its name, or return None if not found.

        Args:
            name: Permission name in format "resource:action"

        Returns:
            The permission object or None
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_if_not_exists(
        self, resource: str, action: str, description: Optional[str] = None
    ) -> Permission:
        """
        Create a new permission if it doesn't already exist.

        Args:
            resource: The resource this permission applies to
            action: The action this permission allows
            description: Optional description

        Returns:
            The new or existing permission
        """
        name = f"{resource}:{action}"

        # Check if permission already exists
        existing = await self.find_by_name(name)
        if existing:
            return existing

        # Create new permission
        permission = Permission(
            resource=resource, action=action, name=name, description=description
        )
        self.session.add(permission)
        await self.session.flush()

        return permission


class RoleRepository(BaseRepository[Role]):
    """Repository for database role operations."""

    async def get_by_name(self, name: str) -> Role:
        """
        Get a role by its name.

        Args:
            name: Role name

        Returns:
            The role object

        Raises:
            NotFoundError: If role doesn't exist
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()

        if role is None:
            raise NotFoundError(resource_type="Role", resource_id=name)

        return role

    async def find_by_name(self, name: str) -> Optional[Role]:
        """
        Find a role by its name, or return None if not found.

        Args:
            name: Role name

        Returns:
            The role object or None
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_if_not_exists(
        self, name: str, description: Optional[str] = None
    ) -> Role:
        """
        Create a new role if it doesn't already exist.

        Args:
            name: Role name
            description: Optional description

        Returns:
            The new or existing role
        """
        # Check if role already exists
        existing = await self.find_by_name(name)
        if existing:
            return existing

        # Create new role
        role = Role(name=name, description=description)
        self.session.add(role)
        await self.session.flush()

        return role

    async def add_permission(self, role: Role, permission: Permission) -> None:
        """
        Add a permission to a role.

        Args:
            role: The role object
            permission: The permission object to add
        """
        if permission not in role.permissions:
            role.permissions.append(permission)
            await self.session.flush()

    async def remove_permission(self, role: Role, permission: Permission) -> None:
        """
        Remove a permission from a role.

        Args:
            role: The role object
            permission: The permission object to remove
        """
        if permission in role.permissions:
            role.permissions.remove(permission)
            await self.session.flush()

    async def get_permissions(self, role: Role) -> List[Permission]:
        """
        Get all permissions for a role.

        Args:
            role: The role object

        Returns:
            List of permission objects
        """
        await self.session.refresh(role, ["permissions"])
        return role.permissions
