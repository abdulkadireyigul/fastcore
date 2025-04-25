"""
Unit tests for the cache.base module.

Covers:
- BaseCache abstract class 
- Abstract method signatures
- Creating custom cache implementations
"""

from abc import ABC

import pytest

from src.cache.base import BaseCache


class TestBaseCache:
    def test_base_cache_is_abstract(self):
        """Test that BaseCache is an abstract class."""
        assert issubclass(BaseCache, ABC)
        assert BaseCache.__abstractmethods__ == {"get", "set", "delete", "clear"}
        with pytest.raises(TypeError):
            BaseCache()  # Should not be instantiable

    def test_base_cache_method_signatures(self):
        """Test that BaseCache method signatures match expected patterns."""
        # Check signature of get method
        get_sig = BaseCache.get.__annotations__
        assert "key" in get_sig
        assert get_sig["return"].__name__ == "Optional"

        # Check signature of set method
        set_sig = BaseCache.set.__annotations__
        assert "key" in set_sig
        assert "value" in set_sig
        assert "ttl" in set_sig

        # Check signature of delete method
        delete_sig = BaseCache.delete.__annotations__
        assert "key" in delete_sig

        # Check signature of clear method
        clear_sig = BaseCache.clear.__annotations__
        assert "prefix" in clear_sig


class MemoryCache(BaseCache):
    """
    Simple in-memory cache implementation for testing.
    """

    def __init__(self):
        self.storage = {}

    async def get(self, key):
        return self.storage.get(key)

    async def set(self, key, value, ttl=None):
        self.storage[key] = value

    async def delete(self, key):
        if key in self.storage:
            del self.storage[key]

    async def clear(self, prefix=None):
        if prefix:
            self.storage = {
                k: v for k, v in self.storage.items() if not k.startswith(prefix)
            }
        else:
            self.storage = {}


@pytest.mark.asyncio
class TestMemoryCacheImplementation:
    """Test a concrete implementation of BaseCache."""

    async def test_memory_cache_get_set(self):
        """Test basic get/set functionality."""
        cache = MemoryCache()
        await cache.set("test-key", "test-value")
        value = await cache.get("test-key")
        assert value == "test-value"

        value = await cache.get("nonexistent-key")
        assert value is None

    async def test_memory_cache_delete(self):
        """Test delete functionality."""
        cache = MemoryCache()
        await cache.set("test-key", "test-value")
        await cache.delete("test-key")
        value = await cache.get("test-key")
        assert value is None

        # Deleting a nonexistent key should not raise an error
        await cache.delete("nonexistent-key")

    async def test_memory_cache_clear(self):
        """Test clear functionality."""
        cache = MemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("prefix:key3", "value3")

        # Clear all
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("prefix:key3") is None

        # Clear with prefix
        cache = MemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("prefix:key3", "value3")

        await cache.clear("prefix:")
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("prefix:key3") is None
