"""
Tests for cache decorator functionality.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from fastcore.cache.backends import MemoryCache
from fastcore.cache.decorator import cached, invalidate_cache
from fastcore.cache.manager import CacheManager


class TestCachedDecorator:
    """Test the @cached decorator."""

    @pytest.fixture
    def setup_cache_manager(self):
        """Set up a cache manager for testing."""
        # Create a cache manager with a memory cache
        cache_manager = CacheManager(default_backend=MemoryCache())

        # Patch the get_cache_manager function to return our test manager
        with patch(
            "fastcore.cache.decorator.get_cache_manager", return_value=cache_manager
        ):
            yield cache_manager

    def test_cache_hit_miss(self, setup_cache_manager):
        """Test that values are cached and retrieved correctly."""
        call_count = 0

        @cached()
        def test_function(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        # First call should execute the function
        result1 = test_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Second call with same args should return cached result
        result2 = test_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Function not called again

        # Call with different args should execute the function
        result3 = test_function(3, 4)
        assert result3 == 7
        assert call_count == 2

    def test_ttl_expiration(self, setup_cache_manager):
        """Test that cached values expire after TTL."""
        call_count = 0

        @cached(ttl=1)  # 1 second TTL
        def test_function():
            nonlocal call_count
            call_count += 1
            return "result"

        # First call should execute the function
        test_function()
        assert call_count == 1

        # Second call should return cached result
        test_function()
        assert call_count == 1

        # Wait for TTL to expire
        time.sleep(1.1)

        # After expiration, function should be called again
        test_function()
        assert call_count == 2

    def test_key_namespace_and_prefix(self, setup_cache_manager):
        """Test that namespace and key_prefix affect cache key generation."""
        cache_manager = setup_cache_manager

        # Function with namespace
        @cached(namespace="ns1")
        def func_ns1(x):
            return x * 2

        # Same function with different namespace
        @cached(namespace="ns2")
        def func_ns2(x):
            return x * 2

        # Function with prefix
        @cached(key_prefix="prefix1")
        def func_prefix1(x):
            return x * 2

        # Call the functions
        func_ns1(10)
        func_ns2(10)
        func_prefix1(10)

        # Check that different keys were used
        cache = cache_manager._caches["default"]

        # We don't know the exact keys, but we know they should all be different
        # and there should be 3 items in the cache
        assert len(cache._cache) == 3

    def test_skip_args_kwargs(self, setup_cache_manager):
        """Test skipping specific args and kwargs when building cache key."""
        call_count = 0

        @cached(skip_args=[1], skip_kwargs=["skip_me"])
        def test_function(a, b, c, skip_me=None, use_me=None):
            nonlocal call_count
            call_count += 1
            return a + c

        # First call
        result1 = test_function(1, 100, 3, skip_me="x", use_me="y")
        assert result1 == 4
        assert call_count == 1

        # Change skipped args and kwargs - should still be a cache hit
        result2 = test_function(1, 200, 3, skip_me="z", use_me="y")
        assert result2 == 4
        assert call_count == 1

        # Change non-skipped args - should be a cache miss
        result3 = test_function(2, 100, 3, skip_me="x", use_me="y")
        assert result3 == 5
        assert call_count == 2

        # Change non-skipped kwargs - should be a cache miss
        result4 = test_function(1, 100, 3, skip_me="x", use_me="z")
        assert result4 == 4
        assert call_count == 3

    def test_custom_key_builder(self, setup_cache_manager):
        """Test using a custom key builder function."""
        call_count = 0

        # Custom key builder that only uses the first argument
        def key_builder(func, *args, **kwargs):
            return f"custom:{args[0]}"

        @cached(key_builder=key_builder)
        def test_function(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        # First call
        result1 = test_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Change second arg - should be a cache hit because key only uses first arg
        result2 = test_function(1, 3)
        assert result2 == 3  # Note: returns cached result (1+2), not 1+3
        assert call_count == 1

        # Change first arg - should be a cache miss
        result3 = test_function(2, 3)
        assert result3 == 5
        assert call_count == 2

    def test_cache_invalidation_via_method(self, setup_cache_manager):
        """Test invalidating the cache via the invalidate method."""
        call_count = 0

        @cached()
        def test_function(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        # First call
        result1 = test_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Should be cached
        result2 = test_function(1, 2)
        assert result2 == 3
        assert call_count == 1

        # Invalidate the cache
        test_function.invalidate(1, 2)  # type: ignore

        # Should execute again
        result3 = test_function(1, 2)
        assert result3 == 3
        assert call_count == 2

    def test_invalidate_cache_function(self, setup_cache_manager):
        """Test invalidating cache with the invalidate_cache function."""
        call_count = 0

        @cached()
        def test_function(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        # First call
        result1 = test_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Should be cached
        result2 = test_function(1, 2)
        assert result2 == 3
        assert call_count == 1

        # Invalidate the cache
        invalidate_cache(test_function, 1, 2)

        # Should execute again
        result3 = test_function(1, 2)
        assert result3 == 3
        assert call_count == 2

    def test_invalidate_cache_for_undecorated_function(self, setup_cache_manager):
        """Test invalidating cache for an undecorated function."""
        cache_manager = setup_cache_manager

        # Manually set a cache entry
        key = "module.func:123"
        cache_manager.set(key, "value")

        # Mock function that wasn't decorated
        def mock_func():
            pass

        # Mock the key generation to return our test key
        with patch("fastcore.cache.decorator._generate_cache_key", return_value=key):
            # Should work even though the function wasn't decorated
            result = invalidate_cache(mock_func)
            assert result is True

            # Key should be gone
            assert not cache_manager.exists(key)

    def test_named_cache(self, setup_cache_manager):
        """Test using a specific named cache."""
        cache_manager = setup_cache_manager

        # Add a named cache
        named_cache = MemoryCache()
        cache_manager.add_cache("named", named_cache)

        call_count = 0

        @cached(cache_name="named")
        def test_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # Call the function
        result = test_function(10)
        assert result == 20
        assert call_count == 1

        # Result should be in named cache, not default
        default_cache = cache_manager.get_cache("default")
        assert len(default_cache._cache) == 0

        # Check it's in the named cache
        assert len(named_cache._cache) == 1
