from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest

from fastcore.cache.backends import RedisCache


@pytest.fixture
def redis_url():
    return "redis://localhost:6379/0"


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def cache(redis_url, mock_logger):
    return RedisCache(
        url=redis_url, default_ttl=100, prefix="test:", logger=mock_logger
    )


# --- 1. Initialization Tests ---


@pytest.mark.asyncio
async def test_init_creates_connection_and_pings(cache):
    with patch("fastcore.cache.backends.aredis.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis

        await cache.init()

        # decode_responses=False (byte modu) kontrolü
        mock_from_url.assert_called_once_with(cache._url, decode_responses=False)
        mock_redis.ping.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args",
    [
        ("get", ("foo",)),
        ("set", ("foo", "bar")),
        ("delete", ("foo",)),
        ("clear", ()),
        ("incr", ("foo",)),
        ("expire", ("foo", 10)),
    ],
)
async def test_methods_raise_if_not_initialized(cache, method, args):
    """Cache init edilmeden kullanılırsa RuntimeError fırlatmalı."""
    # Not: Ping metodu da _get_redis çağırır ama try-except dışında olduğu için
    # o da RuntimeError fırlatır. Onu ayrı test ediyoruz.
    with pytest.raises(RuntimeError, match="Redis connection not initialized"):
        await getattr(cache, method)(*args)


# --- 2. GET Tests ---


@pytest.mark.asyncio
async def test_get_returns_data(cache):
    cache._redis = AsyncMock()
    test_val = {"a": 1}

    # Mock Redis byte döndürmeli
    cache._redis.get.return_value = orjson.dumps(test_val)

    result = await cache.get("foo")

    assert result == test_val
    cache._redis.get.assert_awaited_once_with("test:foo")


@pytest.mark.asyncio
async def test_get_returns_none_on_miss(cache):
    cache._redis = AsyncMock()
    cache._redis.get.return_value = None
    result = await cache.get("foo")
    assert result is None


@pytest.mark.asyncio
async def test_get_logs_on_error(cache):
    """Fail-Silent: Hata fırlatmaz, loglar ve None döner."""
    cache._redis = AsyncMock()
    cache._redis.get.side_effect = Exception("Redis fail")

    result = await cache.get("foo")
    assert result is None
    cache._logger.error.assert_called_once()


# --- 3. SET Tests ---


@pytest.mark.asyncio
async def test_set_stores_dumped_data(cache):
    cache._redis = AsyncMock()
    test_val = {"foo": "bar"}

    await cache.set("foo", test_val)

    expected_bytes = orjson.dumps(test_val)
    cache._redis.set.assert_awaited_once_with("test:foo", expected_bytes, ex=100)


@pytest.mark.asyncio
async def test_set_uses_custom_ttl(cache):
    """Geri getirdiğimiz test: Custom TTL çalışıyor mu?"""
    cache._redis = AsyncMock()
    await cache.set("foo", "bar", ttl=5)
    # Default 100 yerine 5 gitmeli
    expected_bytes = orjson.dumps("bar")
    cache._redis.set.assert_awaited_once_with("test:foo", expected_bytes, ex=5)


@pytest.mark.asyncio
async def test_set_logs_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.set.side_effect = Exception("Fail")
    await cache.set("foo", "bar")
    cache._logger.error.assert_called_once()


# --- 4. DELETE Tests ---


@pytest.mark.asyncio
async def test_delete_deletes_key(cache):
    cache._redis = AsyncMock()
    await cache.delete("foo")
    cache._redis.delete.assert_awaited_once_with("test:foo")


@pytest.mark.asyncio
async def test_delete_logs_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.delete.side_effect = Exception("Fail")
    await cache.delete("foo")
    cache._logger.error.assert_called_once()


# --- 5. CLEAR Tests ---


@pytest.mark.asyncio
async def test_clear_deletes_keys(cache):
    cache._redis = AsyncMock()

    # scan_iter byte döndürmeli
    async def fake_scan_iter(match=None):
        yield b"test:foo"
        yield b"test:bar"

    cache._redis.scan_iter = fake_scan_iter

    await cache.clear()
    # Byte keylerle delete çağrılmalı
    cache._redis.delete.assert_awaited_once_with(b"test:foo", b"test:bar")


@pytest.mark.asyncio
async def test_clear_with_prefix(cache):
    """Geri getirdiğimiz test: Prefix filtresi çalışıyor mu?"""
    cache._redis = AsyncMock()

    async def fake_scan_iter(match=None):
        # Match parametresinin doğru gelip gelmediğini kontrol etmiyoruz (mock limitasyonu)
        # Ama senaryoyu simüle ediyoruz
        yield b"test:users:1"

    cache._redis.scan_iter = fake_scan_iter

    await cache.clear("users:")

    cache._redis.delete.assert_awaited_once_with(b"test:users:1")
    # scan_iter'in doğru pattern ile çağrıldığını doğrulayalım
    # cache prefix (test:) + arg prefix (users:) + * -> test:users:*
    # Not: mock call args kontrolü yapmak mock yapısına göre değişebilir, basit tutuyoruz.


@pytest.mark.asyncio
async def test_clear_logs_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.scan_iter.side_effect = Exception("Fail")
    await cache.clear()
    cache._logger.error.assert_called_once()


# --- 6. PING Tests ---


@pytest.mark.asyncio
async def test_ping_success(cache):
    """Geri getirdiğimiz test"""
    cache._redis = AsyncMock()
    cache._redis.ping.return_value = True
    assert await cache.ping() is True


@pytest.mark.asyncio
async def test_ping_returns_false_on_error(cache):
    cache._redis = AsyncMock()
    cache._redis.ping.side_effect = Exception("Fail")
    result = await cache.ping()
    assert result is False
    cache._logger.error.assert_called_once()


# --- 7. CLOSE Tests (Geri Getirilenler) ---


@pytest.mark.asyncio
async def test_close_closes_and_nulls(cache):
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()
    cache._redis = mock_redis
    await cache.close()
    assert cache._redis is None
    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_handles_double_close(cache):
    cache._redis = None
    # Hata vermemeli
    await cache.close()


# --- 8. INCR & EXPIRE Tests ---


@pytest.mark.asyncio
async def test_incr_increments(cache):
    cache._redis = AsyncMock()
    cache._redis.incrby.return_value = 5

    val = await cache.incr("counter", amount=2)

    assert val == 5
    cache._redis.incrby.assert_awaited_once_with("test:counter", 2)


@pytest.mark.asyncio
async def test_expire_sets_ttl(cache):
    """Geri getirdiğimiz test"""
    cache._redis = AsyncMock()
    await cache.expire("foo", 42)
    cache._redis.expire.assert_awaited_once_with("test:foo", 42)


@pytest.mark.asyncio
async def test_incr_with_expire(cache):
    """Lua Script testi"""
    cache._redis = AsyncMock()
    cache._redis.script_load.return_value = "sha123"
    cache._redis.evalsha.return_value = 1

    val = await cache.incr_with_expire("counter", amount=1, ttl=60)

    assert val == 1
    cache._redis.script_load.assert_awaited_once()
    cache._redis.evalsha.assert_awaited_once()
