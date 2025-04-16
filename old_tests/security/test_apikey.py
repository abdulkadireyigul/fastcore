"""
Tests for API key authentication in the security module.
"""

from datetime import UTC, datetime, timedelta  # Added UTC import
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import APIKeyHeader

from fastcore.security.apikey import APIKey, APIKeyAuth, api_key_header, get_api_key


class TestAPIKey:
    """Test APIKey model."""

    def test_api_key_creation(self):
        """Test creating an API key."""
        api_key = APIKey(name="Test API Key")

        # Check default fields
        assert api_key.key_id
        assert api_key.api_key
        assert api_key.name == "Test API Key"
        assert api_key.enabled is True
        assert api_key.created_at
        assert not api_key.last_used_at
        assert isinstance(api_key.permissions, list)
        assert isinstance(api_key.metadata, dict)

    def test_api_key_expiry(self):
        """Test API key expiration checking."""
        # Key without expiration
        api_key = APIKey(name="No Expiry Key")
        assert not api_key.is_expired

        # Expired key
        yesterday = datetime.now(UTC) - timedelta(days=1)  # Updated to use UTC
        expired_key = APIKey(name="Expired Key", expires_at=yesterday)
        assert expired_key.is_expired

        # Future expiration
        tomorrow = datetime.now(UTC) + timedelta(days=1)  # Updated to use UTC
        future_key = APIKey(name="Future Key", expires_at=tomorrow)
        assert not future_key.is_expired

    def test_last_used_update(self):
        """Test updating the last used timestamp."""
        api_key = APIKey(name="Test Key")
        assert not api_key.last_used_at

        # Update last used time
        api_key.update_last_used()
        assert api_key.last_used_at
        assert isinstance(api_key.last_used_at, datetime)

    def test_has_permission(self):
        """Test permission checking for API keys."""
        # Key with no permissions
        no_perms_key = APIKey(name="No Permissions")
        assert not no_perms_key.has_permission("test:read")

        # Key with specific permission
        specific_key = APIKey(
            name="Specific Permission", permissions=["users:read", "items:write"]
        )
        assert specific_key.has_permission("users:read")
        assert specific_key.has_permission("items:write")
        assert not specific_key.has_permission("users:write")

        # Key with wildcard resource permission
        wildcard_resource_key = APIKey(
            name="Wildcard Resource", permissions=["users:*"]
        )
        assert wildcard_resource_key.has_permission("users:read")
        assert wildcard_resource_key.has_permission("users:write")
        assert not wildcard_resource_key.has_permission("items:read")

        # Key with global wildcard permission
        global_wildcard_key = APIKey(name="Global Wildcard", permissions=["*:*"])
        assert global_wildcard_key.has_permission("anything:goes")
        assert global_wildcard_key.has_permission("users:read")


class TestAPIKeyAuth:
    """Test APIKeyAuth manager."""

    @pytest.fixture
    def api_key_auth(self):
        """Create an API key authentication manager."""
        return APIKeyAuth()

    def test_create_api_key(self, api_key_auth):
        """Test creating an API key."""
        api_key = api_key_auth.create_api_key(
            name="Test Service",
            permissions=["users:read", "items:write"],
            metadata={"service": "test-service"},
        )

        # Check key was created properly
        assert isinstance(api_key, APIKey)
        assert api_key.name == "Test Service"
        assert "users:read" in api_key.permissions
        assert "items:write" in api_key.permissions
        assert api_key.metadata["service"] == "test-service"

        # Key should be stored in the manager
        assert api_key_auth.get_api_key(api_key.api_key) == api_key

    def test_get_api_key(self, api_key_auth):
        """Test retrieving an API key."""
        # Create a key
        api_key = api_key_auth.create_api_key(name="Test Key")

        # Should find the key
        found_key = api_key_auth.get_api_key(api_key.api_key)
        assert found_key == api_key

        # Should return None for nonexistent key
        assert api_key_auth.get_api_key("nonexistent-key") is None

    def test_validate_api_key(self, api_key_auth):
        """Test validating an API key."""
        # Create keys with different states
        valid_key = api_key_auth.create_api_key(name="Valid Key")

        disabled_key = api_key_auth.create_api_key(name="Disabled Key")
        disabled_key.enabled = False

        yesterday = datetime.now(UTC) - timedelta(days=1)  # Updated to use UTC
        expired_key = api_key_auth.create_api_key(
            name="Expired Key", expires_at=yesterday
        )

        # Valid key should validate
        is_valid, key_data = api_key_auth.validate_api_key(valid_key.api_key)
        assert is_valid
        assert key_data == valid_key

        # Disabled key should not validate
        is_valid, key_data = api_key_auth.validate_api_key(disabled_key.api_key)
        assert not is_valid
        assert key_data == disabled_key

        # Expired key should not validate
        is_valid, key_data = api_key_auth.validate_api_key(expired_key.api_key)
        assert not is_valid
        assert key_data == expired_key

        # Nonexistent key should not validate
        is_valid, key_data = api_key_auth.validate_api_key("nonexistent-key")
        assert not is_valid
        assert key_data is None

        # Validation should update last_used_at for valid keys
        old_last_used = valid_key.last_used_at
        api_key_auth.validate_api_key(valid_key.api_key)
        assert valid_key.last_used_at is not None
        if old_last_used:
            assert valid_key.last_used_at >= old_last_used

    def test_revoke_api_key(self, api_key_auth):
        """Test revoking an API key."""
        # Create a key
        api_key = api_key_auth.create_api_key(name="Test Key")

        # Revoke it
        success = api_key_auth.revoke_api_key(api_key.key_id)
        assert success

        # Key should exist but be disabled
        stored_key = api_key_auth.get_api_key(api_key.api_key)
        assert stored_key
        assert not stored_key.enabled

        # Should return False for nonexistent key
        assert not api_key_auth.revoke_api_key("nonexistent-id")

    def test_delete_api_key(self, api_key_auth):
        """Test deleting an API key."""
        # Create a key
        api_key = api_key_auth.create_api_key(name="Test Key")

        # Delete it
        success = api_key_auth.delete_api_key(api_key.key_id)
        assert success

        # Key should no longer exist
        assert not api_key_auth.get_api_key(api_key.api_key)

        # Should return False for nonexistent key
        assert not api_key_auth.delete_api_key("nonexistent-id")

    def test_list_api_keys(self, api_key_auth):
        """Test listing all API keys."""
        # Create some keys
        key1 = api_key_auth.create_api_key(name="Key 1")
        key2 = api_key_auth.create_api_key(name="Key 2")

        # List keys
        keys = api_key_auth.list_api_keys()
        assert len(keys) == 2
        assert key1 in keys
        assert key2 in keys


@pytest.fixture
def mock_api_key_header():
    """Mock the API key header security scheme."""
    with patch.object(APIKeyHeader, "__call__", autospec=True) as mock:
        yield mock


class TestAPIKeyDependency:
    """Test the FastAPI dependency for API key authentication."""

    def setup_method(self):
        """Set up for each test."""
        # Create a test API key
        self.api_key_auth = APIKeyAuth()
        self.api_key = self.api_key_auth.create_api_key(
            name="Test API Key", permissions=["test:read"]
        )

    def test_get_api_key_valid(self, mock_api_key_header):
        """Test getting a valid API key."""
        # Mock the header to return our API key
        mock_api_key_header.return_value = self.api_key.api_key

        # Should return the API key
        with patch("fastcore.security.apikey._api_key_auth", self.api_key_auth):
            result = get_api_key(self.api_key.api_key)
            assert result == self.api_key

    def test_get_api_key_missing(self, mock_api_key_header):
        """Test error when API key is missing."""
        # Mock the header to return None (missing header)
        mock_api_key_header.return_value = None

        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            get_api_key(None)

        # Check exception details
        assert excinfo.value.status_code == 401
        assert "missing" in excinfo.value.detail.lower()

    def test_get_api_key_invalid(self, mock_api_key_header):
        """Test error when API key is invalid."""
        # Mock the header to return an invalid key
        mock_api_key_header.return_value = "invalid-api-key"

        # Should raise HTTPException
        with patch("fastcore.security.apikey._api_key_auth", self.api_key_auth):
            with pytest.raises(HTTPException) as excinfo:
                get_api_key("invalid-api-key")

        # Check exception details
        assert excinfo.value.status_code == 401
        assert "invalid" in excinfo.value.detail.lower()
