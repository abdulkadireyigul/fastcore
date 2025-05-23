"""
User authentication utilities.

This module provides flexible interfaces for user authentication that work with
application-defined user models rather than imposing a specific structure.

Limitations:
- Only password-based JWT authentication is included by default
- No OAuth2 authorization code, implicit, or client credentials flows
- No social login (Google, Facebook, etc.)
- No multi-factor authentication
- No user registration or management flows (only protocols/interfaces)
- No advanced RBAC or permission system
- No API key support
- Stateless JWT blacklisting/revocation requires stateful DB tracking
"""

import abc
from typing import Any, Dict, Generic, Optional, Protocol, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.errors.exceptions import AppError
from fastcore.logging.manager import ensure_logger

# Configure logger
logger = ensure_logger(None, __name__)

# Generic type for user models
UserModelT = TypeVar("UserModelT")


class UserAuthentication(Protocol[UserModelT]):
    """
    Protocol defining the user authentication interface.

    Features:
    - Works with any user model defined by the application
    - Supports async authentication and user lookup

    Limitations:
    - Only password-based JWT authentication is included by default
    - No user registration or management flows (only protocols/interfaces)
    - No advanced RBAC or permission system
    """

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[UserModelT]:
        """
        Authenticate a user with the provided credentials.

        Args:
            credentials: Dictionary containing authentication credentials
                        (typically username/email and password)

        Returns:
            User model instance if authentication succeeds, None otherwise
        """
        ...

    async def get_user_by_id(self, user_id: int) -> Optional[UserModelT]:
        """
        Get a user by their ID.

        Args:
            user_id: The user's unique identifier

        Returns:
            User model instance if found, None otherwise
        """
        ...

    def get_user_id(self, user: UserModelT) -> int:
        """
        Extract the user ID from a user model instance.

        Args:
            user: User model instance

        Returns:
            Integer representation of the user ID
        """
        ...


class AuthenticationError(AppError):
    """
    Exception raised for authentication errors.

    Features:
    - Used for signaling authentication failures

    Limitations:
    - Only password-based JWT authentication is included by default
    - No advanced RBAC or permission system
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details, status_code=401)


class BaseUserAuthentication(abc.ABC, Generic[UserModelT]):
    """
    Abstract base class for user authentication.

    Features:
    - Provides a base for implementing custom authentication logic

    Limitations:
    - Only password-based JWT authentication is included by default
    - No user registration or management flows (only protocols/interfaces)
    - No advanced RBAC or permission system
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the authentication handler.

        Args:
            session: Database session for user operations
        """
        self.session = session

    @abc.abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[UserModelT]:
        """
        Authenticate a user with the provided credentials.

        Args:
            credentials: Dictionary containing authentication credentials

        Returns:
            User model instance if authentication succeeds, None otherwise
        """
        pass

    @abc.abstractmethod
    async def get_user_by_id(self, user_id: int) -> Optional[UserModelT]:
        """
        Get a user by their ID.

        Args:
            user_id: The user's unique identifier

        Returns:
            User model instance if found, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_user_id(self, user: UserModelT) -> int:
        """
        Extract the user ID from a user model instance.

        Args:
            user: User model instance

        Returns:
            String representation of the user ID
        """
        pass
