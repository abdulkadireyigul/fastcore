from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseCache(ABC):
    """
    Abstract base class for cache backends.

    Defines the contract that all cache backend implementations must follow.
    This ensures consistency across different storage mechanisms (e.g., Redis, Memory).
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: The unique identifier for the cached item.

        Returns:
            The cached value if it exists, otherwise None.
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache.

        Args:
            key: The unique identifier for the item.
            value: The data to store (backend handles serialization).
            ttl: Time-to-live in seconds. If None, uses the default TTL.
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete a specific value from the cache.

        Args:
            key: The unique identifier of the item to remove.
        """
        pass

    @abstractmethod
    async def clear(self, prefix: Optional[str] = None) -> None:
        """
        Clear keys from the cache.

        Args:
            prefix: If provided, only keys starting with this prefix are deleted.
                    If None, the entire cache is cleared (use with caution).
        """
        pass

    @abstractmethod
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a key's integer value.

        Args:
            key: The identifier of the counter.
            amount: The amount to increment by (default is 1).

        Returns:
            The new value of the counter, or None if the operation failed.
        """
        pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> None:
        """
        Set a Time-To-Live (expiration) on an existing key.

        Args:
            key: The identifier of the item.
            ttl: The time in seconds after which the key should expire.
        """
        pass

    @abstractmethod
    async def incr_with_expire(
        self, key: str, amount: int = 1, ttl: Optional[int] = None
    ) -> Optional[int]:
        """
        Atomically increment a key and set its TTL if it's a new key.

        This is useful for rate limiting patterns where the first increment
        must also start the expiration timer.

        Args:
            key: The identifier of the counter.
            amount: The amount to increment.
            ttl: The expiration time in seconds.

        Returns:
            The new value of the counter, or None if the operation failed.
        """
        pass
