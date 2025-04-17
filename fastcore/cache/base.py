from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseCache(ABC):
    """
    Abstract base class for cache backends.

    Defines the basic cache operations that backends should implement.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value in cache with an optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from cache by key."""
        pass

    @abstractmethod
    async def clear(self, prefix: Optional[str] = None) -> None:
        """Remove all keys matching the given prefix (or entire cache if no prefix)."""
        pass
