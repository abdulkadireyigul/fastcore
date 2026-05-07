"""
Unit tests for the cache.base module.

Covers:
- BaseCache abstract class 
- Abstract method signatures
- Creating custom cache implementations
"""

from abc import ABC
from typing import Optional

import pytest

from fastcore.cache.base import BaseCache


class TestBaseCache:
    def test_base_cache_is_abstract(self):
        """Test that BaseCache is an abstract class."""
        assert issubclass(BaseCache, ABC)
        assert BaseCache.__abstractmethods__ == {
            "get",
            "set",
            "delete",
            "clear",
            "incr",
            "expire",
            "incr_with_expire",
        }
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

        incr_sig = BaseCache.incr.__annotations__
        assert "key" in incr_sig
        assert "amount" in incr_sig

        expire_sig = BaseCache.expire.__annotations__
        assert "key" in expire_sig
        assert "ttl" in expire_sig

        incr_expire_sig = BaseCache.incr_with_expire.__annotations__
        assert "key" in incr_expire_sig
        assert "amount" in incr_expire_sig
        assert "ttl" in incr_expire_sig


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

    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        val = self.storage.get(key, 0)
        if not isinstance(val, int):
            try:
                val = int(val)
            except (ValueError, TypeError):
                # Fail-Silent mantığına göre None dönmeli veya hata fırlatmalı.
                # BaseCache sözleşmesine uymak için basit int simülasyonu yapıyoruz.
                return None

        new_val = val + amount
        self.storage[key] = new_val
        return new_val

    async def expire(self, key: str, ttl: int) -> None:
        # MemoryCache basit bir mock olduğu için TTL mantığını simüle etmiyoruz,
        # ama metodun var olması şart.
        if key not in self.storage:
            return  # Redis expire key yoksa hiçbir şey yapmaz (veya 0 döner)
        pass

    async def incr_with_expire(
        self, key: str, amount: int = 1, ttl: Optional[int] = None
    ) -> Optional[int]:
        # MemoryCache'de atomiklik ve TTL simülasyonu basittir
        # Sadece incr çağırıyoruz (TTL'i yoksayıyoruz çünkü bu basit bir mock)
        return await self.incr(key, amount)


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

    async def test_memory_cache_incr(self):
        cache = MemoryCache()
        await cache.set("counter", 10)
        new_val = await cache.incr("counter")
        assert new_val == 11

        # Key yoksa oluşturup 1 yapmalı (Redis davranışı)
        val2 = await cache.incr("new_counter")
        assert val2 == 1

    async def test_memory_cache_incr_with_expire(self):
        """Test the newly added abstract method implementation."""
        cache = MemoryCache()
        val = await cache.incr_with_expire("counter", 1, ttl=60)
        assert val == 1
        val2 = await cache.incr_with_expire("counter", 1, ttl=60)
        assert val2 == 2
