"""
Permission and role management for FastAPI applications.

This module provides utilities for implementing role-based access control (RBAC)
in FastAPI applications.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union

from fastcore.errors.exceptions import AppError, NotFoundError, ValidationError
from fastcore.logging import get_logger

# Get a logger for this module
logger = get_logger(__name__)


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


class Role:
    """
    A user role with associated permissions.

    This class represents a role that can be assigned to users, with
    a set of permissions that determine what actions the user can perform.

    Example:
        ```python
        # Define roles and permissions
        admin_role = Role("admin", [
            Permission("users", "read"),
            Permission("users", "write"),
            Permission("users", "delete"),
        ])

        # Check if a role has a permission
        if admin_role.has_permission("users:read"):
            # Admin can read users
            ...
        ```
    """

    def __init__(self, name: str, permissions: List[Union[Permission, str]] = None):
        """
        Initialize a new role.

        Args:
            name: The name of this role
            permissions: Optional list of permissions for this role
        """
        self.name = name
        self._permissions: Set[str] = set()

        if permissions:
            for perm in permissions:
                self.add_permission(perm)

    def add_permission(self, permission: Union[Permission, str]) -> None:
        """
        Add a permission to this role.

        Args:
            permission: The permission to add, either a Permission object or string
        """
        if isinstance(permission, Permission):
            self._permissions.add(permission.name)
        else:
            self._permissions.add(permission)

    def remove_permission(self, permission: Union[Permission, str]) -> None:
        """
        Remove a permission from this role.

        Args:
            permission: The permission to remove, either a Permission object or string
        """
        if isinstance(permission, Permission):
            self._permissions.discard(permission.name)
        else:
            self._permissions.discard(permission)

    def has_permission(self, permission: Union[Permission, str]) -> bool:
        """
        Check if this role has a specific permission.

        Args:
            permission: The permission to check for, either a Permission object or string

        Returns:
            True if the role has this permission, False otherwise
        """
        perm_name = (
            permission.name if isinstance(permission, Permission) else permission
        )

        # Check for exact permission
        if perm_name in self._permissions:
            return True

        # Check for wildcard permissions
        if perm_name.count(":") == 1:
            resource, action = perm_name.split(":")
            if f"{resource}:*" in self._permissions:
                return True

        # Check for global wildcard
        if "*:*" in self._permissions:
            return True

        return False

    @property
    def permissions(self) -> List[str]:
        """Get all permissions for this role."""
        return list(self._permissions)

    def __str__(self) -> str:
        """Get the string representation of this role."""
        return self.name

    def __repr__(self) -> str:
        """Get the debug representation of this role."""
        return f"Role({self.name!r}, {list(self._permissions)!r})"


class RolePermission:
    """
    A utility class for managing roles and permissions.

    This class provides methods for defining roles and permissions, assigning
    roles to users, and checking if users have specific permissions.

    Example:
        ```python
        # Create a role manager
        role_manager = RolePermission()

        # Define roles and permissions
        role_manager.add_role("admin", ["users:*", "products:*"])
        role_manager.add_role("editor", ["users:read", "products:write"])

        # Check permissions for a user with roles
        user_roles = ["editor"]
        if role_manager.check_permission(user_roles, "products:write"):
            # User can write products
            ...
        ```
    """

    def __init__(self):
        """Initialize a new role permission manager."""
        self._roles: Dict[str, Role] = {}

    def add_role(
        self, name: str, permissions: List[Union[Permission, str]] = None
    ) -> Role:
        """
        Add a new role.

        Args:
            name: The name of the role
            permissions: Optional list of permissions for this role

        Returns:
            The created role

        Raises:
            ValidationError: If a role with this name already exists
        """
        if name in self._roles:
            raise ValidationError(f"Role '{name}' already exists")

        role = Role(name, permissions)
        self._roles[name] = role
        logger.debug(f"Added role {name} with permissions {permissions}")
        return role

    def get_role(self, name: str) -> Optional[Role]:
        """
        Get a role by name.

        Args:
            name: The name of the role

        Returns:
            The role, or None if it doesn't exist
        """
        return self._roles.get(name)

    def add_permission_to_role(
        self, role_name: str, permission: Union[Permission, str]
    ) -> None:
        """
        Add a permission to an existing role.

        Args:
            role_name: The name of the role
            permission: The permission to add

        Raises:
            NotFoundError: If the role doesn't exist
        """
        role = self.get_role(role_name)
        if not role:
            raise NotFoundError(f"Role '{role_name}' not found")

        role.add_permission(permission)
        logger.debug(f"Added permission {permission} to role {role_name}")

    def check_permission(
        self, user_roles: List[str], permission: Union[Permission, str]
    ) -> bool:
        """
        Check if a user with the given roles has a specific permission.

        Args:
            user_roles: The roles assigned to the user
            permission: The permission to check for

        Returns:
            True if the user has the permission, False otherwise
        """
        # Special case: superuser role always has all permissions
        if "superuser" in user_roles:
            return True

        for role_name in user_roles:
            role = self.get_role(role_name)
            if role and role.has_permission(permission):
                return True

        return False

    def get_role_permissions(self, role_name: str) -> List[str]:
        """
        Get all permissions for a specific role.

        Args:
            role_name: The name of the role

        Returns:
            A list of permission strings for this role

        Raises:
            NotFoundError: If the role doesn't exist
        """
        role = self.get_role(role_name)
        if not role:
            raise NotFoundError(f"Role '{role_name}' not found")

        return role.permissions

    def get_user_permissions(self, user_roles: List[str]) -> List[str]:
        """
        Get all permissions for a user with the given roles.

        Args:
            user_roles: The roles assigned to the user

        Returns:
            A list of all permission strings for the user's roles
        """
        permissions = set()

        for role_name in user_roles:
            role = self.get_role(role_name)
            if role:
                permissions.update(role.permissions)

        return list(permissions)
