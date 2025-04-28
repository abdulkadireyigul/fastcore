import json
from unittest.mock import AsyncMock, patch

import pytest

from fastcore.cache.backends import RedisCache


@pytest.fixture
def redis_url():
    return "redis://localhost:6379/0"


@pytest.fixture
def cache(redis_url):
    return RedisCache(url=redis_url, default_ttl=100, prefix="test:")


@pytest.mark.asyncio
async def test_init_creates_connection_and_pings(cache):
    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        await cache.init()
        mock_from_url.assert_called_once_with(
            cache._url, encoding="utf-8", decode_responses=True
        )
        mock_redis.ping.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args",
    [
        ("get", ("foo",)),
        ("set", ("foo", "bar")),
        ("delete", ("foo",)),
        ("clear", ()),
        ("ping", ()),
    ],
)
async def test_methods_raise_if_not_initialized(cache, method, args):
    with pytest.raises(RuntimeError, match="Redis connection is not initialized"):
        await getattr(cache, method)(*args)


@pytest.mark.asyncio
async def test_get_returns_string(cache):
    cache._redis = AsyncMock()
    cache._redis.get.return_value = "bar"
    result = await cache.get("foo")
    assert result == "bar"
    cache._redis.get.assert_awaited_once_with("test:foo")


@pytest.mark.asyncio
async def test_get_returns_json(cache):
    cache._redis = AsyncMock()
    value = {"a": 1}
    cache._redis.get.return_value = json.dumps(value)
    result = await cache.get("foo")
    assert result == value


@pytest.mark.asyncio
async def test_get_returns_none_on_miss(cache):
    cache._redis = AsyncMock()
    cache._redis.get.return_value = None
    result = await cache.get("foo")
    assert result is None


@pytest.mark.asyncio
async def test_get_raises_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.get.side_effect = Exception("fail")
    with pytest.raises(Exception):
        await cache.get("foo")


@pytest.mark.asyncio
async def test_set_stores_string(cache):
    cache._redis = AsyncMock()
    await cache.set("foo", "bar")
    cache._redis.set.assert_awaited_once_with("test:foo", "bar", ex=100)


@pytest.mark.asyncio
async def test_set_stores_json(cache):
    cache._redis = AsyncMock()
    value = {"a": 1}
    await cache.set("foo", value)
    cache._redis.set.assert_awaited_once_with("test:foo", json.dumps(value), ex=100)


@pytest.mark.asyncio
async def test_set_uses_custom_ttl(cache):
    cache._redis = AsyncMock()
    await cache.set("foo", "bar", ttl=5)
    cache._redis.set.assert_awaited_once_with("test:foo", "bar", ex=5)


@pytest.mark.asyncio
async def test_set_raises_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.set.side_effect = Exception("fail")
    with pytest.raises(Exception):
        await cache.set("foo", "bar")


@pytest.mark.asyncio
async def test_delete_deletes_key(cache):
    cache._redis = AsyncMock()
    await cache.delete("foo")
    cache._redis.delete.assert_awaited_once_with("test:foo")


@pytest.mark.asyncio
async def test_delete_raises_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.delete.side_effect = Exception("fail")
    with pytest.raises(Exception):
        await cache.delete("foo")


@pytest.mark.asyncio
async def test_clear_deletes_keys(cache):
    cache._redis = AsyncMock()
    deleted_keys = []

    async def fake_scan_iter(match=None):
        for k in ["test:foo", "test:bar"]:
            yield k

    cache._redis.scan_iter = fake_scan_iter

    async def fake_delete(key):
        deleted_keys.append(key)

    cache._redis.delete.side_effect = fake_delete
    await cache.clear()
    assert set(deleted_keys) == {"test:foo", "test:bar"}
    assert cache._redis.delete.await_count == 2


@pytest.mark.asyncio
async def test_clear_with_prefix(cache):
    cache._redis = AsyncMock()
    deleted_keys = []

    async def fake_scan_iter(match=None):
        for k in ["test:bar:baz"]:
            yield k

    cache._redis.scan_iter = fake_scan_iter

    async def fake_delete(key):
        deleted_keys.append(key)

    cache._redis.delete.side_effect = fake_delete
    await cache.clear("bar:")
    assert deleted_keys == ["test:bar:baz"]
    assert cache._redis.delete.await_count == 1


@pytest.mark.asyncio
async def test_clear_raises_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.scan_iter.side_effect = Exception("fail")
    with pytest.raises(Exception):
        await cache.clear()


@pytest.mark.asyncio
async def test_ping_success(cache):
    cache._redis = AsyncMock()
    cache._redis.ping.return_value = True
    assert await cache.ping() is True


@pytest.mark.asyncio
async def test_ping_error_returns_false(cache):
    cache._redis = AsyncMock()
    cache._redis.ping.side_effect = Exception("fail")
    assert await cache.ping() is False


@pytest.mark.asyncio
async def test_close_closes_and_nulls(cache):
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()
    cache._redis = mock_redis
    await cache.close()
    assert cache._redis is None


@pytest.mark.asyncio
async def test_close_handles_double_close(cache):
    cache._redis = None
    # Should not raise
    await cache.close()


@pytest.mark.asyncio
async def test_close_raises_on_error(cache):
    class DummyPool:
        async def disconnect(self):
            raise Exception("disconnect error")

    mock_redis = AsyncMock()
    mock_redis.connection_pool = DummyPool()
    cache._redis = mock_redis
    with pytest.raises(Exception, match="disconnect error"):
        await cache.close()
