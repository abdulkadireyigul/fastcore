"""
UUID User Authentication Interfaces.

This module defines Protocols and Abstract Base Classes for user authentication
strategies in systems using UUIDs as primary keys.

It mirrors the logic of `fastcore.security.users` (Integer-based) but enforces
UUID types, providing flexibility to handle both string and UUID object representations
to ensure seamless integration with JWT payloads.
"""

import abc
import uuid
from typing import Any, Dict, Generic, Optional, Protocol, TypeVar, Union

from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.logging.manager import ensure_logger

logger = ensure_logger(None, __name__)

# Generic type for user models to ensure type safety in implementations
UserModelT = TypeVar("UserModelT")


class UUIDUserAuthentication(Protocol[UserModelT]):
    """
    Protocol defining the contract for UUID-based user authentication.

    Any class implementing this protocol can be injected as a dependency
    for token services requiring user verification.
    """

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[UserModelT]:
        """
        Validate user credentials (e.g., username/password) and return the user instance.

        Args:
            credentials (Dict[str, Any]): A dictionary containing login credentials.

        Returns:
            Optional[UserModelT]: The user instance if authentication succeeds, None otherwise.
        """
        ...

    async def get_user_by_id(
        self, user_id: Union[uuid.UUID, str]
    ) -> Optional[UserModelT]:
        """
        Retrieve a user by their unique UUID identifier.

        Accepts both `uuid.UUID` objects and `str` representations to allow
        direct usage of JWT 'sub' claims without manual conversion.

        Args:
            user_id (Union[uuid.UUID, str]): The user's unique identifier.

        Returns:
            Optional[UserModelT]: The user model instance if found, None otherwise.
        """
        ...

    def get_user_id(self, user: UserModelT) -> Union[uuid.UUID, str]:
        """
        Extract the unique identifier from a user model instance.

        Args:
            user (UserModelT): The user model instance.

        Returns:
            Union[uuid.UUID, str]: The UUID object or string representation of the ID.
        """
        ...


class BaseUUIDUserAuthentication(abc.ABC, Generic[UserModelT]):
    """
    Abstract Base Class for UUID user authentication.

    This class provides a skeletal implementation for authentication handlers.
    Applications should subclass this and implement the abstract methods
    to define specific business logic (e.g., password hashing, DB lookups).
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the authentication handler.

        Args:
            session (AsyncSession): The active database session for user operations.
        """
        self.session = session

    @abc.abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[UserModelT]:
        """
        Authenticate a user with the provided credentials.

        Must be implemented by the application to handle password verification.
        """
        pass

    @abc.abstractmethod
    async def get_user_by_id(
        self, user_id: Union[uuid.UUID, str]
    ) -> Optional[UserModelT]:
        """
        Retrieve a user by their UUID.

        Must be implemented by the application to handle database lookups.
        Should handle both string and UUID object inputs.
        """
        pass

    @abc.abstractmethod
    def get_user_id(self, user: UserModelT) -> Union[uuid.UUID, str]:
        """
        Extract the UUID from a user model instance.

        Must be implemented by the application to map the model's ID field.
        """
        pass
