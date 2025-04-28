"""
Unit tests for the cache.decorators module.

Covers:
- Cache decorator functionality
- Key generation and hashing
- Cache hit and miss scenarios
- TTL handling
- Prefix handling
- Error handling
"""

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastcore.cache.decorators import cache


@pytest.fixture
def mock_cache():
    """Mock cache instance."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    return mock


class TestCacheDecorator:
    @pytest.mark.asyncio
    async def test_cache_decorator_hit(self, mock_cache):
        """Test cache decorator with a cache hit."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache hit
            mock_cache.get.return_value = "cached_result"

            # Create a function with cache decorator
            @cache()
            async def test_func(a, b):
                # This should not be called when there's a cache hit
                assert False, "Function should not be called on cache hit"
                return a + b

            # Call the function
            result = await test_func(1, 2)

            # Verify result is from cache
            assert result == "cached_result"
            mock_cache.get.assert_awaited_once()
            mock_cache.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cache_decorator_miss(self, mock_cache):
        """Test cache decorator with a cache miss."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache miss
            mock_cache.get.return_value = None

            # Create a function with cache decorator
            @cache()
            async def test_func(a, b):
                return a + b

            # Call the function
            result = await test_func(1, 2)

            # Verify function was called and result was cached
            assert result == 3
            mock_cache.get.assert_awaited_once()
            mock_cache.set.assert_awaited_once()

            # Verify value was cached
            _, args, kwargs = mock_cache.set.mock_calls[0]
            assert args[1] == 3  # Second argument to set should be the function result

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, mock_cache):
        """Test that cache keys are generated correctly based on function and arguments."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache miss
            mock_cache.get.return_value = None

            # Create a function with cache decorator
            @cache()
            async def test_func(a, b, c=None):
                return a + b

            # Call the function
            await test_func(1, 2, c=3)

            # Verify key generation
            get_call_args = mock_cache.get.call_args[0]
            set_call_args = mock_cache.set.call_args[0]

            # The key should be the same for get and set
            assert get_call_args[0] == set_call_args[0]

            # Generate expected key manually
            key_data = {
                "func": "test_cache_decorators.test_func",
                "args": (1, 2),
                "kwargs": {"c": 3},
            }
            key_str = json.dumps(key_data, default=str, sort_keys=True)
            key_hash = hashlib.sha256(key_str.encode()).hexdigest()

            # Key should be a hash
            assert len(get_call_args[0]) == 64

            # Different arguments should produce different keys
            mock_cache.get.reset_mock()
            mock_cache.set.reset_mock()
            await test_func(2, 3, c=4)
            get_call_args2 = mock_cache.get.call_args[0]
            assert get_call_args[0] != get_call_args2[0]

    @pytest.mark.asyncio
    async def test_cache_ttl(self, mock_cache):
        """Test cache decorator with custom TTL."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache miss
            mock_cache.get.return_value = None

            # Create a function with cache decorator and custom TTL
            @cache(ttl=60)
            async def test_func(a, b):
                return a + b

            # Call the function
            await test_func(1, 2)

            # Verify TTL was passed to cache.set
            _, _, kwargs = mock_cache.set.mock_calls[0]
            assert kwargs["ttl"] == 60

    @pytest.mark.asyncio
    async def test_cache_prefix(self, mock_cache):
        """Test cache decorator with custom prefix."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache miss
            mock_cache.get.return_value = None

            # Create a function with cache decorator and custom prefix
            @cache(prefix="test_prefix:")
            async def test_func(a, b):
                return a + b

            # Call the function
            await test_func(1, 2)

            # Verify prefix was used in key
            get_call_args = mock_cache.get.call_args[0]
            assert get_call_args[0].startswith("test_prefix:")

    @pytest.mark.asyncio
    async def test_cache_with_complex_arguments(self, mock_cache):
        """Test cache decorator with complex arguments (lists, dicts, etc.)."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache miss
            mock_cache.get.return_value = None

            # Create a function with cache decorator
            @cache()
            async def test_func(a, b=None):
                return {"result": a}

            # Call with complex arguments
            complex_arg = {"key": "value", "nested": {"a": 1, "b": [1, 2, 3]}}
            await test_func(complex_arg, b=[1, 2, 3])

            # Should not raise any errors
            mock_cache.get.assert_awaited_once()
            mock_cache.set.assert_awaited_once()

            # Verify the value was cached correctly
            _, args, _ = mock_cache.set.mock_calls[0]
            assert args[1] == {"result": complex_arg}

    @pytest.mark.asyncio
    async def test_cache_get_error(self, mock_cache):
        """Test error handling when cache.get raises an exception."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache.get to raise an exception
            mock_cache.get.side_effect = Exception("Cache get error")

            # Create a function with cache decorator
            @cache()
            async def test_func(a, b):
                return a + b

            # Call the function
            result = await test_func(1, 2)

            # Function should still execute and return a result, even if cache fails
            assert result == 3
            mock_cache.get.assert_awaited_once()

            # We should attempt to cache the result even if get failed
            mock_cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_set_error(self, mock_cache):
        """Test error handling when cache.set raises an exception."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache.get to miss and cache.set to raise an exception
            mock_cache.get.return_value = None
            mock_cache.set.side_effect = Exception("Cache set error")

            # Create a function with cache decorator
            @cache()
            async def test_func(a, b):
                return a + b

            # Call the function
            result = await test_func(1, 2)

            # Function should still execute and return a result, even if cache fails
            assert result == 3
            mock_cache.get.assert_awaited_once()
            mock_cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_non_json_serializable(self, mock_cache):
        """Test caching with results that aren't JSON serializable."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Setup cache miss
            mock_cache.get.return_value = None

            # Create a class that isn't JSON serializable
            class NonSerializable:
                def __init__(self, value):
                    self.value = value

            # Create a function with cache decorator
            @cache()
            async def test_func():
                return NonSerializable(42)

            # Call the function
            result = await test_func()

            # Function should execute and return a result
            assert isinstance(result, NonSerializable)
            assert result.value == 42

            # Cache should still be used, but will handle the error internally
            mock_cache.get.assert_awaited_once()
            mock_cache.set.assert_awaited_once()
