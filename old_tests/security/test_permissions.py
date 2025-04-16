"""
Tests for permissions and role-based access control.
"""

import pytest

from fastcore.errors.exceptions import NotFoundError, ValidationError
from fastcore.security.permissions import Permission, Role, RolePermission


class TestPermission:
    """Test the Permission class."""

    def test_permission_creation(self):
        """Test creating a permission."""
        permission = Permission("users", "read")

        assert permission.resource == "users"
        assert permission.action == "read"
        assert permission.name == "users:read"
        assert str(permission) == "users:read"
        assert repr(permission).startswith("Permission(")

    def test_permission_check(self):
        """Test checking a permission against user permissions."""
        permission = Permission("users", "read")

        # Direct permission match
        assert permission.check(["users:read", "items:write"])

        # Resource wildcard match
        assert permission.check(["users:*", "items:write"])

        # Global wildcard match
        assert permission.check(["*:*"])

        # No match
        assert not permission.check(["users:write", "items:read"])
        assert not permission.check([])

    def test_permission_equality(self):
        """Test permission equality checking."""
        p1 = Permission("users", "read")
        p2 = Permission("users", "read")
        p3 = Permission("users", "write")

        # Same permissions should be equal
        assert p1 == p2

        # Different permissions should not be equal
        assert p1 != p3

        # String comparison should work
        assert p1 == "users:read"
        assert p1 != "users:write"

        # Other types should not be equal
        assert p1 != 123


class TestRole:
    """Test the Role class."""

    def test_role_creation(self):
        """Test creating a role."""
        # Empty role
        role = Role("user")
        assert role.name == "user"
        assert role.permissions == []

        # Role with Permission objects
        role = Role(
            "editor", [Permission("users", "read"), Permission("items", "write")]
        )
        assert role.name == "editor"
        assert "users:read" in role.permissions
        assert "items:write" in role.permissions

        # Role with permission strings
        role = Role("admin", ["users:*", "items:*"])
        assert role.name == "admin"
        assert "users:*" in role.permissions
        assert "items:*" in role.permissions

    def test_add_permission(self):
        """Test adding permissions to a role."""
        role = Role("user")

        # Add Permission object
        role.add_permission(Permission("users", "read"))
        assert "users:read" in role.permissions

        # Add permission string
        role.add_permission("items:write")
        assert "items:write" in role.permissions

    def test_remove_permission(self):
        """Test removing permissions from a role."""
        role = Role("admin", ["users:read", "users:write", "items:*"])

        # Remove Permission object
        role.remove_permission(Permission("users", "write"))
        assert "users:write" not in role.permissions
        assert "users:read" in role.permissions

        # Remove permission string
        role.remove_permission("items:*")
        assert "items:*" not in role.permissions

        # Removing nonexistent permission should be a no-op
        role.remove_permission("nonexistent:permission")

    def test_has_permission(self):
        """Test checking if a role has a permission."""
        role = Role("editor", ["users:read", "items:*", "comments:write"])

        # Direct match
        assert role.has_permission("users:read")
        assert role.has_permission(Permission("users", "read"))

        # Wildcard match
        assert role.has_permission("items:read")
        assert role.has_permission("items:write")
        assert role.has_permission(Permission("items", "delete"))

        # No match
        assert not role.has_permission("users:write")
        assert not role.has_permission(Permission("users", "delete"))

        # Global wildcard
        role.add_permission("*:*")
        assert role.has_permission("anything:goes")
        assert role.has_permission(Permission("random", "access"))


class TestRolePermission:
    """Test the RolePermission manager."""

    @pytest.fixture
    def role_manager(self):
        """Create a role permission manager."""
        manager = RolePermission()

        # Add some basic roles
        manager.add_role("user", ["items:read"])
        manager.add_role("editor", ["items:read", "items:write", "comments:*"])
        manager.add_role("admin", ["users:*", "items:*", "comments:*"])
        manager.add_role("superuser", ["*:*"])

        return manager

    def test_add_role(self, role_manager):
        """Test adding a role."""
        # Add a new role
        role = role_manager.add_role("moderator", ["comments:*", "users:read"])
        assert role.name == "moderator"
        assert "comments:*" in role.permissions
        assert "users:read" in role.permissions

        # Adding an existing role should raise an error
        with pytest.raises(ValidationError):  # Changed from AppError
            role_manager.add_role("user")

    def test_get_role(self, role_manager):
        """Test getting a role by name."""
        # Existing role
        role = role_manager.get_role("editor")
        assert role.name == "editor"
        assert "items:write" in role.permissions

        # Nonexistent role
        assert role_manager.get_role("nonexistent") is None

    def test_add_permission_to_role(self, role_manager):
        """Test adding a permission to a role."""
        # Add to existing role
        role_manager.add_permission_to_role("user", "profiles:read")
        role = role_manager.get_role("user")
        assert "profiles:read" in role.permissions

        # Add to nonexistent role should raise error
        with pytest.raises(NotFoundError):  # Changed from AppError
            role_manager.add_permission_to_role("nonexistent", "test:read")

    def test_check_permission(self, role_manager):
        """Test checking if a user with roles has a permission."""
        # Single role
        assert role_manager.check_permission(["user"], "items:read")
        assert not role_manager.check_permission(["user"], "items:write")

        # Multiple roles
        assert role_manager.check_permission(["user", "editor"], "items:write")
        assert not role_manager.check_permission(["user", "editor"], "users:read")

        # Wildcard permission
        assert role_manager.check_permission(["editor"], "comments:read")
        assert role_manager.check_permission(["editor"], "comments:write")

        # Superuser always has permission
        assert role_manager.check_permission(["superuser"], "anything:goes")

        # No roles
        assert not role_manager.check_permission([], "items:read")

        # Nonexistent roles
        assert not role_manager.check_permission(["nonexistent"], "items:read")

    def test_get_role_permissions(self, role_manager):
        """Test getting all permissions for a role."""
        # Existing role
        perms = role_manager.get_role_permissions("editor")
        assert "items:read" in perms
        assert "items:write" in perms
        assert "comments:*" in perms

        # Nonexistent role should raise error
        with pytest.raises(NotFoundError):  # Changed from AppError
            role_manager.get_role_permissions("nonexistent")

    def test_get_user_permissions(self, role_manager):
        """Test getting all permissions for a user with roles."""
        # Single role
        user_perms = role_manager.get_user_permissions(["user"])
        assert len(user_perms) == 1
        assert "items:read" in user_perms

        # Multiple roles
        user_perms = role_manager.get_user_permissions(["user", "editor"])
        assert len(user_perms) >= 3
        assert "items:read" in user_perms
        assert "items:write" in user_perms
        assert "comments:*" in user_perms

        # Nonexistent roles
        user_perms = role_manager.get_user_permissions(["nonexistent"])
        assert len(user_perms) == 0

        # Mix of existing and nonexistent roles
        user_perms = role_manager.get_user_permissions(["user", "nonexistent"])
        assert len(user_perms) == 1
        assert "items:read" in user_perms
