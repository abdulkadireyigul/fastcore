"""
Tests for security dependencies for FastAPI applications.
"""

import json
from datetime import UTC, datetime, timedelta  # Added UTC import
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from fastcore.errors.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)
from fastcore.security.auth import JWTAuth, JWTConfig, JWTPayload
from fastcore.security.dependencies import (
    User,
    configure_jwt_auth,
    configure_user_retriever,
    get_current_active_user,
    get_current_superuser,
    get_current_token,
    get_current_user,
    require_permissions,
)


@pytest.fixture
def jwt_config():
    """Create a JWT config for testing."""
    config = JWTConfig()
    config.SECRET_KEY = "test-secret-key"
    config.ALGORITHM = "HS256"
    config.TOKEN_URL = "auth/test-token"
    config.ISSUER = "test-issuer"
    config.AUDIENCE = "test-audience"  # Changed from list to string
    return config


@pytest.fixture
def jwt_auth(jwt_config):
    """Create a JWT auth instance for testing."""
    return JWTAuth(jwt_config)


@pytest.fixture
def configure_test_auth(jwt_auth):
    """Configure JWT auth for testing."""
    configure_jwt_auth(jwt_auth)
    yield
    # Reset the global JWT auth
    with patch("fastcore.security.dependencies._jwt_auth", None):
        pass


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        disabled=False,
        roles=["user", "editor"],
        permissions=["items:read", "items:write"],
    )


@pytest.fixture
def disabled_user():
    """Create a disabled user for testing."""
    return User(
        id="disabled123",
        username="disabled",
        email="disabled@example.com",
        full_name="Disabled User",
        disabled=True,
        roles=["user"],
    )


@pytest.fixture
def admin_user():
    """Create an admin user for testing."""
    return User(
        id="admin123",
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        disabled=False,
        roles=["admin", "superuser"],
        permissions=["*:*"],
    )


@pytest.fixture
def mock_user_retriever(sample_user, disabled_user, admin_user):
    """Mock the user retriever function."""

    def get_user_by_id(user_id: str) -> User:
        users = {
            "user123": sample_user,
            "disabled123": disabled_user,
            "admin123": admin_user,
        }
        if user_id not in users:
            raise HTTPException(status_code=404, detail="User not found")
        return users[user_id]

    configure_user_retriever(get_user_by_id)
    yield get_user_by_id
    # Reset the global user retriever
    with patch("fastcore.security.dependencies._user_retriever", None):
        pass


class TestGetCurrentToken:
    """Test the get_current_token dependency."""

    def test_get_current_token_success(self, jwt_auth, configure_test_auth):
        """Test successful token extraction."""
        # Create a token
        token = jwt_auth.create_access_token(
            subject="user123",
            scopes=["users:read"],
        )

        # Create security scopes
        security_scopes = SecurityScopes(scopes=["users:read"])

        # Call the dependency
        payload = get_current_token(security_scopes, token)

        # Check the payload
        assert isinstance(payload, JWTPayload)
        assert payload.sub == "user123"
        assert payload.scope == "users:read"

    def test_get_current_token_missing_scope(self, jwt_auth, configure_test_auth):
        """Test token with missing required scope."""
        # Create a token with limited scope
        token = jwt_auth.create_access_token(
            subject="user123",
            scopes=["users:read"],
        )

        # Create security scopes with additional required scope
        security_scopes = SecurityScopes(scopes=["users:read", "users:write"])

        # Should raise HTTPException
        with pytest.raises(AuthorizationError) as excinfo:  # Changed from HTTPException
            get_current_token(security_scopes, token)

        assert "permissions" in excinfo.value.message.lower()

    def test_get_current_token_invalid(self, jwt_auth, configure_test_auth):
        """Test with invalid token."""
        # Invalid token
        token = "invalid.token.string"

        # Create security scopes
        security_scopes = SecurityScopes()

        # Should raise HTTPException
        with pytest.raises(
            AuthenticationError
        ) as excinfo:  # Changed from HTTPException
            get_current_token(security_scopes, token)

        assert "invalid" in excinfo.value.message.lower()

    def test_get_current_token_unconfigured(self):
        """Test when JWT auth is not configured."""
        # No configuration
        with patch("fastcore.security.dependencies._jwt_auth", None):
            # Should raise HTTPException
            with pytest.raises(HTTPException) as excinfo:
                get_current_token(SecurityScopes(), "token")

            assert excinfo.value.status_code == 500
            assert "not configured" in excinfo.value.detail.lower()


class TestGetCurrentUser:
    """Test the get_current_user dependency."""

    @pytest.fixture
    def token_payload(self):
        """Create a token payload for testing."""
        return JWTPayload(
            sub="user123",
            exp=datetime.now(UTC) + timedelta(minutes=30),  # Updated to use UTC
            iat=datetime.now(UTC),  # Updated to use UTC
            type="access",
            role="editor",
            permissions=["items:read", "comments:write"],
        )

    def test_get_current_user_success(
        self, token_payload, mock_user_retriever, sample_user
    ):
        """Test successful user retrieval."""
        # Call the dependency
        user = get_current_user(token_payload)

        # Check the user
        assert user.id == sample_user.id
        assert user.username == sample_user.username
        # Role from token should be added to user roles
        assert "editor" in user.roles
        # Permissions from token should be added to user permissions
        assert "comments:write" in user.permissions

    def test_get_current_user_not_found(self, mock_user_retriever):
        """Test when user is not found."""
        # Create a token with nonexistent user ID
        token_payload = JWTPayload(
            sub="nonexistent",
            exp=datetime.now(UTC) + timedelta(minutes=30),  # Updated to use UTC
            iat=datetime.now(UTC),  # Updated to use UTC
            type="access",
        )

        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            get_current_user(token_payload)

        assert excinfo.value.status_code == 404
        assert "not found" in excinfo.value.detail.lower()

    def test_get_current_user_unconfigured(self, token_payload):
        """Test when user retriever is not configured."""
        # No configuration
        with patch("fastcore.security.dependencies._user_retriever", None):
            # Should raise HTTPException
            with pytest.raises(HTTPException) as excinfo:
                get_current_user(token_payload)

            assert excinfo.value.status_code == 500
            assert "not configured" in excinfo.value.detail.lower()


class TestGetCurrentActiveUser:
    """Test the get_current_active_user dependency."""

    def test_get_current_active_user_success(self, sample_user):
        """Test successful active user retrieval."""
        # Call the dependency
        user = get_current_active_user(sample_user)

        # Should return the same user
        assert user == sample_user

    def test_get_current_active_user_disabled(self, disabled_user):
        """Test with disabled user."""
        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            get_current_active_user(disabled_user)

        assert excinfo.value.status_code == 403
        assert "inactive" in excinfo.value.detail.lower()


class TestGetCurrentSuperuser:
    """Test the get_current_superuser dependency."""

    def test_get_current_superuser_success(self, admin_user):
        """Test successful superuser retrieval."""
        # Call the dependency
        user = get_current_superuser(admin_user)

        # Should return the same user
        assert user == admin_user

    def test_get_current_superuser_not_admin(self, sample_user):
        """Test with non-admin user."""
        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            get_current_superuser(sample_user)

        assert excinfo.value.status_code == 403
        assert "superuser" in excinfo.value.detail.lower()


class TestRequirePermissions:
    """Test the require_permissions dependency factory."""

    def test_require_permissions_success(self, sample_user):
        """Test successful permission check."""
        # User has items:read permission
        check_permissions = require_permissions(["items:read"])

        # Should not raise exception
        check_permissions(sample_user)

    def test_require_permissions_missing(self, sample_user):
        """Test with missing permissions."""
        # User doesn't have users:write permission
        check_permissions = require_permissions(["users:write"])

        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            check_permissions(sample_user)

        assert excinfo.value.status_code == 403
        assert "permissions" in excinfo.value.detail.lower()

    def test_require_permissions_superuser(self, admin_user):
        """Test that superuser can access anything."""
        # Require a permission not explicitly granted
        check_permissions = require_permissions(["anything:goes"])

        # Should not raise exception for superuser
        check_permissions(admin_user)

    def test_require_permissions_multiple(self, sample_user):
        """Test with multiple required permissions."""
        # User has items:read but not users:read
        check_permissions = require_permissions(["items:read", "users:read"])

        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            check_permissions(sample_user)

        assert excinfo.value.status_code == 403
        assert "users:read" in excinfo.value.detail
