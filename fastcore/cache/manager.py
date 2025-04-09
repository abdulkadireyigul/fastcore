"""
Cache manager for centralized access to cache backends.

This module provides a CacheManager class that serves as a central point
for accessing different cache backends. It also provides functions for
configuring the global cache manager.
"""

import inspect
from typing import Any, Dict, Optional, Type, Union, cast

from fastcore.logging import get_logger

from .backends import CacheBackend, MemoryCache, NullCache, RedisCache

logger = get_logger(__name__)

# Global cache manager instance
_cache_manager = None


class CacheManager:
    """
    Centralized cache manager for working with multiple cache backends.

    The cache manager provides a way to work with different cache backends
    through a single interface. It allows registering multiple named caches
    and performs operations on the appropriate backend.
    """

    def __init__(self, default_backend: Optional[CacheBackend] = None):
        """
        Initialize the cache manager.

        Args:
            default_backend: The default cache backend to use
                             (defaults to MemoryCache)
        """
        self._caches: Dict[str, CacheBackend] = {}

        # Set the default cache backend
        if default_backend is None:
            default_backend = MemoryCache()

        self.add_cache("default", default_backend)

    def add_cache(self, name: str, backend: CacheBackend) -> None:
        """
        Add a named cache backend.

        Args:
            name: The name to identify this cache
            backend: The cache backend instance
        """
        self._caches[name] = backend
        logger.debug(f"Added cache backend '{name}' of type {type(backend).__name__}")

    def get_cache(self, name: str = "default") -> CacheBackend:
        """
        Get a cache backend by name.

        Args:
            name: The name of the cache backend

        Returns:
            The cache backend instance
        """
        if name not in self._caches:
            logger.warning(f"Cache '{name}' not found, using default")
            return self._caches["default"]

        return self._caches[name]

    def get(self, key: str, cache_name: str = "default") -> Any:
        """
        Get a value from the cache.

        Args:
            key: The cache key
            cache_name: The name of the cache backend to use

        Returns:
            The cached value or None if not found
        """
        cache = self.get_cache(cache_name)
        result = cache.get(key)

        # Handle both tuple return and direct value return from mocks in tests
        if isinstance(result, tuple) and len(result) == 2:
            hit, value = result
            return value if hit else None

        # For mocks that don't return a tuple in tests
        logger.warning(f"Cache backend returned unexpected format: {result}")
        return None

    def get_with_info(self, key: str, cache_name: str = "default") -> tuple[bool, Any]:
        """
        Get a value from the cache with hit/miss information.

        Args:
            key: The cache key
            cache_name: The name of the cache backend to use

        Returns:
            A tuple of (hit, value) where hit is a boolean indicating whether
            the key was found and value is the cached value or None
        """
        cache = self.get_cache(cache_name)
        result = cache.get(key)

        # Handle both tuple return and direct value return from mocks in tests
        if isinstance(result, tuple) and len(result) == 2:
            return result

        # For mocks that don't return a tuple in tests
        logger.warning(f"Cache backend returned unexpected format: {result}")
        return False, None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_name: str = "default",
    ) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Optional time-to-live in seconds
            cache_name: The name of the cache backend to use
        """
        cache = self.get_cache(cache_name)
        cache.set(key, value, ttl)

    def delete(self, key: str, cache_name: str = "default") -> bool:
        """
        Delete a value from the cache.

        Args:
            key: The cache key
            cache_name: The name of the cache backend to use

        Returns:
            True if the key was found and deleted, False otherwise
        """
        cache = self.get_cache(cache_name)
        return cache.delete(key)

    def clear(self, cache_name: Optional[str] = None) -> None:
        """
        Clear all values from the cache.

        Args:
            cache_name: The name of the cache backend to clear,
                       or None to clear all caches
        """
        if cache_name is not None:
            # Clear only the specified cache
            cache = self.get_cache(cache_name)
            cache.clear()
            logger.debug(f"Cleared cache '{cache_name}'")
        else:
            # Clear all caches
            for name, cache in self._caches.items():
                cache.clear()
                logger.debug(f"Cleared cache '{name}'")

    def exists(self, key: str, cache_name: str = "default") -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: The cache key
            cache_name: The name of the cache backend to use

        Returns:
            True if the key exists, False otherwise
        """
        cache = self.get_cache(cache_name)
        return cache.exists(key)


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.

    Returns:
        The global cache manager instance
    """
    global _cache_manager

    if _cache_manager is None:
        logger.debug("Initializing default cache manager with NullCache")
        _cache_manager = CacheManager(default_backend=NullCache())

    return _cache_manager


def configure_cache(
    cache_type: str = "memory", cache_name: str = "default", **kwargs
) -> CacheManager:
    """
    Configure the global cache manager.

    Args:
        cache_type: The type of cache backend to use
                   ("memory", "redis", or "null")
        cache_name: The name to give to this cache
        **kwargs: Additional arguments to pass to the cache backend constructor

    Returns:
        The configured cache manager

    Raises:
        ValueError: If the cache type is unknown
    """
    global _cache_manager

    # Get or create the cache manager
    cache_manager = get_cache_manager()

    # Create the appropriate cache backend
    if cache_type == "memory":
        backend = MemoryCache(**kwargs)
    elif cache_type == "redis":
        backend = RedisCache(**kwargs)
    elif cache_type == "null":
        backend = NullCache()
    else:
        raise ValueError(f"Unknown cache type: {cache_type}")

    # Add the cache backend to the manager
    cache_manager.add_cache(cache_name, backend)

    logger.info(f"Configured {cache_type} cache with name '{cache_name}'")

    return cache_manager
