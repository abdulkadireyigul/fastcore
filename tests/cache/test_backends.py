"""
Tests for cache backend implementations.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

# Check if redis is available
try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

from fastcore.cache.backends import CacheBackend, MemoryCache, NullCache, RedisCache

# Skip tests that require Redis if the module is not installed
redis_not_installed = pytest.mark.skipif(
    not HAS_REDIS, reason="Redis package is not installed"
)


class TestNullCache:
    """Test the NullCache backend."""

    @pytest.fixture
    def cache(self):
        """Create a NullCache instance for testing."""
        return NullCache()

    def test_get(self, cache):
        """Test that get always returns a miss."""
        hit, value = cache.get("any_key")
        assert hit is False
        assert value is None

    def test_set(self, cache):
        """Test that set is a no-op."""
        cache.set("key", "value")
        hit, value = cache.get("key")
        assert hit is False
        assert value is None

    def test_delete(self, cache):
        """Test that delete always returns False."""
        result = cache.delete("key")
        assert result is False

    def test_clear(self, cache):
        """Test that clear is a no-op."""
        cache.clear()  # Should not raise any exception

    def test_exists(self, cache):
        """Test that exists always returns False."""
        assert cache.exists("key") is False


class TestMemoryCache:
    """Test the MemoryCache backend."""

    @pytest.fixture
    def cache(self):
        """Create a MemoryCache instance for testing."""
        return MemoryCache(max_size=3)

    def test_get_set(self, cache):
        """Test basic get/set operations."""
        # Set a value
        cache.set("key1", "value1")

        # Get the value
        hit, value = cache.get("key1")
        assert hit is True
        assert value == "value1"

        # Get a non-existent key
        hit, value = cache.get("nonexistent")
        assert hit is False
        assert value is None

    def test_expiration(self, cache):
        """Test that values expire after TTL."""
        # Set a value with a short TTL
        cache.set("key", "value", ttl=1)

        # Verify it's there
        assert cache.exists("key") is True

        # Wait for expiration
        time.sleep(1.1)

        # Verify it's gone
        assert cache.exists("key") is False
        hit, value = cache.get("key")
        assert hit is False
        assert value is None

    def test_lru_eviction(self, cache):
        """Test that least recently used items are evicted when the cache is full."""
        # Fill the cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # All keys should exist
        assert cache.exists("key1") is True
        assert cache.exists("key2") is True
        assert cache.exists("key3") is True

        # Access key1 to make it most recently used
        cache.get("key1")

        # Add another item, which should evict key2 (least recently used)
        cache.set("key4", "value4")

        # key2 should be evicted
        assert cache.exists("key1") is True
        assert cache.exists("key2") is False
        assert cache.exists("key3") is True
        assert cache.exists("key4") is True

    def test_delete(self, cache):
        """Test deleting items from the cache."""
        # Set a value
        cache.set("key", "value")

        # Delete it
        result = cache.delete("key")
        assert result is True
        assert cache.exists("key") is False

        # Deleting non-existent key should return False
        result = cache.delete("nonexistent")
        assert result is False

    def test_clear(self, cache):
        """Test clearing the cache."""
        # Add multiple items
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Clear the cache
        cache.clear()

        # All items should be gone
        assert cache.exists("key1") is False
        assert cache.exists("key2") is False


class TestRedisCache:
    """Test the RedisCache backend with mocked Redis client."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        if not HAS_REDIS:
            pytest.skip("Redis package is not installed")

        with patch("redis.Redis") as mock:
            # Configure the mock instance
            mock_instance = MagicMock()
            mock.return_value = mock_instance

            # Configure ping method
            mock_instance.ping.return_value = True

            yield mock_instance

    @pytest.fixture
    def cache(self, mock_redis):
        """Create a RedisCache instance with the mock Redis client."""
        if not HAS_REDIS:
            pytest.skip("Redis package is not installed")

        with patch("redis.Redis", return_value=mock_redis):
            cache = RedisCache(prefix="test:")
            return cache

    @redis_not_installed
    def test_initialization_with_connection_error(self, mock_redis):
        """Test handling of connection errors during initialization."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            RedisCache()

    @redis_not_installed
    def test_get_hit(self, cache, mock_redis):
        """Test getting a value that exists in the cache."""
        # Setup mock to return a value
        mock_redis.get.return_value = b'"value1"'

        hit, value = cache.get("key")

        # Check that the key was prefixed
        mock_redis.get.assert_called_once_with("test:key")

        # Check the returned result
        assert hit is True
        assert value == "value1"

    @redis_not_installed
    def test_get_miss(self, cache, mock_redis):
        """Test getting a value that doesn't exist in the cache."""
        # Setup mock to return None (key not found)
        mock_redis.get.return_value = None

        hit, value = cache.get("nonexistent")

        # Check the returned result
        assert hit is False
        assert value is None

    @redis_not_installed
    def test_set(self, cache, mock_redis):
        """Test setting a value in the cache."""
        # Set a value without TTL
        cache.set("key", "value")
        mock_redis.set.assert_called_once_with("test:key", '"value"')
        mock_redis.set.reset_mock()

        # Set a value with TTL
        cache.set("key", "value", ttl=60)
        mock_redis.setex.assert_called_once_with("test:key", 60, '"value"')

    @redis_not_installed
    def test_delete(self, cache, mock_redis):
        """Test deleting a value from the cache."""
        # Setup mock to return 1 (key deleted)
        mock_redis.delete.return_value = 1

        result = cache.delete("key")
        mock_redis.delete.assert_called_once_with("test:key")
        assert result is True

        # Setup mock to return 0 (key not found)
        mock_redis.delete.return_value = 0

        result = cache.delete("nonexistent")
        assert result is False

    @redis_not_installed
    def test_clear(self, cache, mock_redis):
        """Test clearing the cache."""
        # Setup mock for scan and delete
        mock_redis.scan.side_effect = [
            (1, [b"test:key1", b"test:key2"]),  # First batch
            (0, [b"test:key3"]),  # Second and final batch
        ]

        cache.clear()

        # Should have called scan twice
        assert mock_redis.scan.call_count == 2

        # Should have called delete with all keys
        mock_redis.delete.assert_any_call(b"test:key1", b"test:key2")
        mock_redis.delete.assert_any_call(b"test:key3")

    @redis_not_installed
    def test_exists(self, cache, mock_redis):
        """Test checking if a key exists in the cache."""
        # Setup mock to return 1 (key exists)
        mock_redis.exists.return_value = 1

        result = cache.exists("key")
        mock_redis.exists.assert_called_once_with("test:key")
        assert result is True

        # Setup mock to return 0 (key doesn't exist)
        mock_redis.exists.return_value = 0

        result = cache.exists("nonexistent")
        assert result is False
