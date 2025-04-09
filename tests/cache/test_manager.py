"""
Tests for cache manager implementation.
"""

from unittest.mock import MagicMock, patch

import pytest

# Check if redis is available
try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

from fastcore.cache.backends import MemoryCache, NullCache, RedisCache
from fastcore.cache.manager import CacheManager, configure_cache, get_cache_manager

# Skip tests that require Redis if the module is not installed
redis_not_installed = pytest.mark.skipif(
    not HAS_REDIS, reason="Redis package is not installed"
)


class TestCacheManager:
    """Test the CacheManager class."""

    @pytest.fixture
    def manager(self):
        """Create a CacheManager for testing."""
        return CacheManager()

    def test_init_default(self):
        """Test initialization with default backend."""
        manager = CacheManager()
        assert isinstance(manager._caches["default"], MemoryCache)

    def test_init_custom_backend(self):
        """Test initialization with a custom backend."""
        backend = NullCache()
        manager = CacheManager(default_backend=backend)
        assert manager._caches["default"] is backend

    def test_add_get_cache(self):
        """Test adding and retrieving a named cache."""
        manager = CacheManager()
        backend = NullCache()

        # Add a named cache
        manager.add_cache("test", backend)

        # Get the cache
        cache = manager.get_cache("test")
        assert cache is backend

    def test_get_nonexistent_cache(self, manager):
        """Test getting a non-existent cache returns the default."""
        cache = manager.get_cache("nonexistent")
        assert isinstance(cache, MemoryCache)

    def test_operations_delegate_to_backend(self, manager):
        """Test that operations are delegated to the backend."""
        # Replace the default cache with a mock
        mock_backend = MagicMock()
        manager.add_cache("default", mock_backend)

        # Test get
        manager.get("key")
        mock_backend.get.assert_called_once_with("key")

        # Test set
        manager.set("key", "value", ttl=60)
        mock_backend.set.assert_called_once_with("key", "value", 60)

        # Test delete
        manager.delete("key")
        mock_backend.delete.assert_called_once_with("key")

        # Test exists
        manager.exists("key")
        mock_backend.exists.assert_called_once_with("key")

    def test_clear_specific_cache(self):
        """Test clearing a specific cache."""
        manager = CacheManager()
        mock_default = MagicMock()
        mock_redis = MagicMock()

        manager.add_cache("default", mock_default)
        manager.add_cache("redis", mock_redis)

        # Clear only the redis cache
        manager.clear("redis")

        # Only redis cache should be cleared
        mock_redis.clear.assert_called_once()
        mock_default.clear.assert_not_called()

    def test_clear_all_caches(self):
        """Test clearing all caches."""
        manager = CacheManager()
        mock_default = MagicMock()
        mock_redis = MagicMock()

        manager.add_cache("default", mock_default)
        manager.add_cache("redis", mock_redis)

        # Clear all caches
        manager.clear()

        # Both caches should be cleared
        mock_default.clear.assert_called_once()
        mock_redis.clear.assert_called_once()

    def test_operations_with_named_cache(self, manager):
        """Test operations with a named cache."""
        # Add a named cache
        named_backend = MagicMock()
        manager.add_cache("named", named_backend)

        # Test get with named cache
        manager.get("key", "named")
        named_backend.get.assert_called_once_with("key")

        # Test set with named cache
        manager.set("key", "value", ttl=60, cache_name="named")
        named_backend.set.assert_called_once_with("key", "value", 60)

        # Test delete with named cache
        manager.delete("key", "named")
        named_backend.delete.assert_called_once_with("key")

        # Test exists with named cache
        manager.exists("key", "named")
        named_backend.exists.assert_called_once_with("key")


class TestGlobalCacheManager:
    """Test the global cache manager functions."""

    def setup_method(self):
        """Reset the global cache manager before each test."""
        # Reset the global cache manager
        import fastcore.cache.manager

        fastcore.cache.manager._cache_manager = None

    def teardown_method(self):
        """Reset the global cache manager after each test."""
        import fastcore.cache.manager

        fastcore.cache.manager._cache_manager = None

    def test_get_cache_manager_unconfigured(self):
        """Test getting the cache manager before it's configured."""
        manager = get_cache_manager()
        assert isinstance(manager, CacheManager)
        assert isinstance(manager.get_cache(), NullCache)

    def test_configure_cache_memory(self):
        """Test configuring the global cache manager with memory backend."""
        configure_cache("memory", max_size=1000)

        manager = get_cache_manager()
        assert isinstance(manager, CacheManager)

        backend = manager.get_cache()
        assert isinstance(backend, MemoryCache)
        assert backend._max_size == 1000

    def test_configure_cache_null(self):
        """Test configuring the global cache manager with null backend."""
        configure_cache("null")

        manager = get_cache_manager()
        backend = manager.get_cache()
        assert isinstance(backend, NullCache)

    @redis_not_installed
    def test_configure_cache_redis(self):
        """Test configuring the global cache manager with Redis backend."""
        if not HAS_REDIS:
            pytest.skip("Redis package is not installed")

        with patch("redis.Redis") as mock_redis_cls:
            # Setup the mock
            mock_redis = MagicMock()
            mock_redis_cls.return_value = mock_redis

            # Configure with Redis backend
            configure_cache(
                "redis",
                host="redis.example.com",
                port=6380,
                db=1,
                password="secret",
                prefix="app:",
            )

            # Check that Redis was initialized with the right parameters
            # Note: prefix is not passed to Redis constructor, it's stored as an attribute
            mock_redis_cls.assert_called_once_with(
                host="redis.example.com", port=6380, db=1, password="secret"
            )

            # Check that the cache manager was configured correctly
            manager = get_cache_manager()
            backend = manager.get_cache()
            assert isinstance(backend, RedisCache)
            assert backend._prefix == "app:"  # Verify the prefix was set correctly

    def test_configure_cache_unknown(self):
        """Test configuring the cache with an unknown backend type."""
        with pytest.raises(ValueError):
            configure_cache("unknown")

    def test_reconfigure_existing_manager(self):
        """Test reconfiguring an existing cache manager."""
        # Configure initially with memory backend
        configure_cache("memory")
        manager1 = get_cache_manager()

        # Reconfigure with null backend
        configure_cache("null")
        manager2 = get_cache_manager()

        # Should be the same manager instance
        assert manager1 is manager2

        # But backend should be updated
        assert isinstance(manager2.get_cache(), NullCache)
