"""
API key authentication for FastAPI applications.

This module provides utilities for implementing API key based authentication
in FastAPI applications.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Union

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field

from fastcore.errors.exceptions import AppError
from fastcore.logging import get_logger

# Get a logger for this module
logger = get_logger(__name__)

# API key header security scheme for FastAPI
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKey(BaseModel):
    """
    Model representing an API key.

    This class defines the structure of an API key, including its value,
    expiration date, and associated metadata.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    name: str
    enabled: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_used_at: Optional[datetime] = None
    permissions: List[str] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if this API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def update_last_used(self) -> None:
        """Update the last used timestamp to the current time."""
        self.last_used_at = datetime.now(UTC)

    def has_permission(self, permission: str) -> bool:
        """
        Check if this API key has a specific permission.

        Args:
            permission: The permission to check for

        Returns:
            True if the API key has this permission, False otherwise
        """
        # If no permissions specified, assume no access
        if not self.permissions:
            return False

        # Check for exact permission
        if permission in self.permissions:
            return True

        # Check for wildcard permissions
        if permission.count(":") == 1:
            resource, action = permission.split(":")
            if f"{resource}:*" in self.permissions:
                return True

        # Check for global wildcard
        if "*:*" in self.permissions:
            return True

        return False


class APIKeyAuth:
    """
    API key authentication manager.

    This class provides methods for creating, validating, and managing API keys.

    Example:
        ```python
        # Create an API key manager
        api_key_auth = APIKeyAuth()

        # Create a new API key
        api_key = api_key_auth.create_api_key("Service Integration", permissions=["users:read"])

        # Validate an API key
        is_valid, key_data = api_key_auth.validate_api_key(api_key_str)
        ```
    """

    def __init__(self):
        """Initialize a new API key authentication manager."""
        self._api_keys: Dict[str, APIKey] = {}

    def create_api_key(
        self,
        name: str,
        permissions: List[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Dict = None,
    ) -> APIKey:
        """
        Create a new API key.

        Args:
            name: A descriptive name for this API key
            permissions: Optional list of permissions for this API key
            expires_at: Optional expiration date for this API key
            metadata: Optional metadata to associate with this API key

        Returns:
            The created API key
        """
        api_key = APIKey(
            name=name,
            expires_at=expires_at,
            permissions=permissions or [],
            metadata=metadata or {},
        )

        self._api_keys[api_key.api_key] = api_key
        logger.info(f"Created new API key: {api_key.key_id} ({name})")

        return api_key

    def get_api_key(self, key_value: str) -> Optional[APIKey]:
        """
        Get an API key by its value.

        Args:
            key_value: The API key value to look up

        Returns:
            The API key, or None if not found
        """
        return self._api_keys.get(key_value)

    def validate_api_key(self, key_value: str) -> tuple[bool, Optional[APIKey]]:
        """
        Validate an API key.

        This method checks if the API key exists, is enabled, and has not expired.

        Args:
            key_value: The API key value to validate

        Returns:
            A tuple of (is_valid, key_data)
        """
        api_key = self.get_api_key(key_value)

        if not api_key:
            return False, None

        if not api_key.enabled:
            logger.warning(f"Attempt to use disabled API key: {api_key.key_id}")
            return False, api_key

        if api_key.is_expired:
            logger.warning(f"Attempt to use expired API key: {api_key.key_id}")
            return False, api_key

        # Update last used timestamp
        api_key.update_last_used()

        return True, api_key

    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key by its ID.

        Args:
            key_id: The ID of the API key to revoke

        Returns:
            True if the key was found and revoked, False otherwise
        """
        for key_value, api_key in list(self._api_keys.items()):
            if api_key.key_id == key_id:
                api_key.enabled = False
                logger.info(f"Revoked API key: {key_id}")
                return True

        return False

    def delete_api_key(self, key_id: str) -> bool:
        """
        Delete an API key by its ID.

        Args:
            key_id: The ID of the API key to delete

        Returns:
            True if the key was found and deleted, False otherwise
        """
        for key_value, api_key in list(self._api_keys.items()):
            if api_key.key_id == key_id:
                del self._api_keys[key_value]
                logger.info(f"Deleted API key: {key_id}")
                return True

        return False

    def list_api_keys(self) -> List[APIKey]:
        """
        Get a list of all API keys.

        Returns:
            A list of all API keys
        """
        return list(self._api_keys.values())


# Singleton API key manager
_api_key_auth = APIKeyAuth()


def get_api_key(api_key_header: str = Security(api_key_header)) -> APIKey:
    """
    FastAPI dependency for API key authentication.

    This dependency extracts and validates an API key from the request headers.

    Args:
        api_key_header: The API key header extracted by FastAPI

    Returns:
        The validated API key

    Raises:
        HTTPException: If the API key is missing or invalid
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "APIKey"},
        )

    is_valid, api_key = _api_key_auth.validate_api_key(api_key_header)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "APIKey"},
        )

    return api_key
