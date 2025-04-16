"""
Cache backend implementations.

This module provides various cache backends including:
- NullCache: A no-op cache that doesn't actually store anything
- MemoryCache: An in-memory cache using LRU eviction policy
- RedisCache: A Redis-backed cache for distributed applications
"""

import json
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from functools import lru_cache
from threading import RLock
from typing import Any, Dict, Optional, Tuple, Union

from fastcore.logging import get_logger

# Import Redis conditionally to make it an optional dependency
try:
    import redis
except ImportError:
    redis = None

logger = get_logger(__name__)


class CacheBackend(ABC):
    """
    Abstract base class for cache backends.

    All cache implementations should inherit from this class
    and implement its abstract methods.
    """

    @abstractmethod
    def get(self, key: str) -> Tuple[bool, Any]:
        """
        Get a value from the cache.

        Args:
            key: The cache key

        Returns:
            A tuple of (hit, value) where hit is a boolean indicating whether
            the key was found and value is the cached value or None
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Optional time-to-live in seconds
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: The cache key

        Returns:
            True if the key was found and deleted, False otherwise
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all values from the cache."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: The cache key

        Returns:
            True if the key exists, False otherwise
        """
        pass


class NullCache(CacheBackend):
    """
    A no-op cache implementation.

    This cache doesn't actually store anything and always returns cache misses.
    It's useful for testing, disabling caching, or as a fallback when no
    cache backend is available.
    """

    def get(self, key: str) -> Tuple[bool, Any]:
        """Always return a cache miss."""
        return False, None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Do nothing."""
        pass

    def delete(self, key: str) -> bool:
        """Always return False (key not found)."""
        return False

    def clear(self) -> None:
        """Do nothing."""
        pass

    def exists(self, key: str) -> bool:
        """Always return False (key not found)."""
        return False


class MemoryCache(CacheBackend):
    """
    In-memory cache with LRU eviction policy.

    This cache stores values in memory with optional TTL expiration.
    It uses an ordered dictionary to track access order for LRU eviction.

    Note:
        This cache is not thread-safe by default. Use a lock when accessing
        from multiple threads.
    """

    def __init__(self, max_size: int = 10000):
        """
        Initialize the memory cache.

        Args:
            max_size: Maximum number of items to store before evicting
        """
        self._cache: Dict[str, Tuple[Any, Optional[float]]] = OrderedDict()
        self._max_size = max_size
        self._lock = RLock()

        logger.info(f"Initialized memory cache with max size {max_size}")

    def get(self, key: str) -> Tuple[bool, Any]:
        """
        Get a value from the cache.

        Args:
            key: The cache key

        Returns:
            A tuple of (hit, value) where hit is a boolean indicating whether
            the key was found and value is the cached value or None
        """
        with self._lock:
            if key not in self._cache:
                return False, None

            value, expiry = self._cache[key]

            # Check if the value has expired
            if expiry is not None and time.time() >= expiry:
                # Remove expired value
                del self._cache[key]
                return False, None

            # Move to end to mark as recently used
            self._cache.move_to_end(key)

            return True, value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Optional time-to-live in seconds
        """
        with self._lock:
            # Calculate expiry time if TTL provided
            expiry = time.time() + ttl if ttl is not None else None

            # If key already exists, update it
            if key in self._cache:
                self._cache[key] = (value, expiry)
                self._cache.move_to_end(key)
                return

            # Evict least recently used item if at max size
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            # Add the new item
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: The cache key

        Returns:
            True if the key was found and deleted, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all values from the cache."""
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: The cache key

        Returns:
            True if the key exists and is not expired, False otherwise
        """
        with self._lock:
            if key not in self._cache:
                return False

            _, expiry = self._cache[key]

            # Check if the value has expired
            if expiry is not None and time.time() >= expiry:
                # Remove expired value
                del self._cache[key]
                return False

            return True


class RedisCache(CacheBackend):
    """
    Redis-backed cache implementation.

    This cache uses Redis as the backend, providing a distributed cache
    that can be shared between multiple application instances.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "fastcore:",
        **kwargs,
    ):
        """
        Initialize the Redis cache.

        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Optional Redis password
            prefix: Key prefix to use for all cache keys
            **kwargs: Additional arguments to pass to Redis constructor

        Raises:
            ImportError: If Redis package is not installed
            ConnectionError: If connection to Redis fails
        """
        if redis is None:
            raise ImportError(
                "Redis package not installed. Install it with: pip install redis"
            )

        self._prefix = prefix

        # Create Redis client
        self._redis = redis.Redis(
            host=host, port=port, db=db, password=password, **kwargs
        )

        # Test connection
        try:
            self._redis.ping()
            logger.info(f"Connected to Redis at {host}:{port} (DB: {db})")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _prefix_key(self, key: str) -> str:
        """
        Add prefix to the key.

        Args:
            key: The original key

        Returns:
            The key with prefix added
        """
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Tuple[bool, Any]:
        """
        Get a value from the cache.

        Args:
            key: The cache key

        Returns:
            A tuple of (hit, value) where hit is a boolean indicating whether
            the key was found and value is the cached value or None
        """
        prefixed_key = self._prefix_key(key)

        try:
            value = self._redis.get(prefixed_key)

            if value is None:
                return False, None

            # Deserialize JSON value
            return True, json.loads(value)
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return False, None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Optional time-to-live in seconds
        """
        prefixed_key = self._prefix_key(key)

        try:
            # Serialize value to JSON
            serialized = json.dumps(value)

            if ttl is not None:
                self._redis.setex(prefixed_key, ttl, serialized)
            else:
                self._redis.set(prefixed_key, serialized)
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: The cache key

        Returns:
            True if the key was found and deleted, False otherwise
        """
        prefixed_key = self._prefix_key(key)

        try:
            result = self._redis.delete(prefixed_key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            return False

    def clear(self) -> None:
        """
        Clear all values with the configured prefix from the cache.

        Note:
            This only deletes keys with the configured prefix, not the entire Redis database.
        """
        try:
            # Find all keys with the prefix
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor, f"{self._prefix}*", 100)

                if keys:
                    self._redis.delete(*keys)

                if cursor == 0:
                    break
        except Exception as e:
            logger.error(
                f"Error clearing keys with prefix {self._prefix} from Redis: {e}"
            )

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: The cache key

        Returns:
            True if the key exists, False otherwise
        """
        prefixed_key = self._prefix_key(key)

        try:
            return bool(self._redis.exists(prefixed_key))
        except Exception as e:
            logger.error(f"Error checking existence of key {key} in Redis: {e}")
            return False
