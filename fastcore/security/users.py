"""
User authentication utilities.

This module provides flexible interfaces for user authentication that work with
application-defined user models rather than imposing a specific structure.
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

    This protocol allows the security module to work with any user model defined
    by the application without requiring a specific structure.
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
    """Exception raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details, status_code=401)


class BaseUserAuthentication(Generic[UserModelT], abc.ABC):
    """
    Base implementation of the UserAuthentication protocol.

    This class provides a foundation for building authentication handlers
    that work with application-defined user models.
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
